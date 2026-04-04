"""
parser.py — Agent 1: PDF 解析器

职责：
  1. 将每份 PDF 逐页渲染为 PNG 图片（200 DPI）
  2. 逐页调用 Qwen-VL-Max，识别文字、LaTeX 公式和图的文字描述
  3. 将多页识别结果合并，切分为按题号索引的结构化数据
  4. 判断该份 PDF 是试题卷还是答案卷
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional

import fitz  # PyMuPDF

from app.agents.state import ExamState
from app.services.vision_service import call_vision_model

logger = logging.getLogger(__name__)

# 每页渲染分辨率（DPI）
RENDER_DPI = 200

# Qwen-VL 识别单页的 Prompt 模板
_PAGE_PROMPT = """\
你是一名专业的试卷 OCR 助手。请仔细识别这张试卷图片中的所有内容，以 JSON 格式输出。

输出要求：
1. 数学公式、符号、方程：必须使用 LaTeX 语法，行内公式用 $...$，独立公式用 $$...$$。
2. 图、表、电路图、示意图：不要试图描述像素，改用 [图: 简要文字描述] 占位符，描述图的内容要点。
3. 严格按照以下 JSON schema 输出，不要有多余的说明文字：

{{
  "page_questions": [
    {{
      "number": "题号（如 '一' / '1' / '(1)' / '1.'，保持原文）",
      "type": "题型（如 填空题/判断题/选择题/计算题/证明题/问答题，如无法判断则 null）",
      "points": 分值（整数，如无则 null）,
      "content": "完整题目正文（含 LaTeX 公式和图占位符）",
      "figure_descriptions": ["图1描述", "图2描述"],
      "answer": "参考答案或解题步骤（仅答案卷有，否则 null）",
      "scoring_criteria": ["给分点1", "给分点2"]
    }}
  ],
  "section_title": "若该页是某大题的标题页，填写大题名称，否则 null",
  "is_answer_page": true 或 false（该页是否属于答案/解析部分）
}}

注意：
- 若一道题跨越多页，请只输出该页能看到的部分，使用 "(续)" 或 "(接上页)" 标注。
- 若该页只有答案而无题目，is_answer_page 设为 true，并将答案内容填入对应题目的 answer 字段。
- 如果是该份试卷的最后一页（已告知），请在输出中额外加一个字段 "is_last_page": true。

这是第 {page_num} 页，共 {total_pages} 页。{last_page_hint}
"""

_LAST_PAGE_HINT = "这是最后一页，请加上 \"is_last_page\": true。"


def render_pdf_to_images(pdf_path: str, dpi: int = RENDER_DPI) -> list[bytes]:
    """
    使用 PyMuPDF 将 PDF 每页渲染为 PNG 字节数组。

    Args:
        pdf_path: PDF 文件路径。
        dpi: 渲染分辨率。

    Returns:
        每页的 PNG 字节数据列表。
    """
    doc = fitz.open(pdf_path)
    images: list[bytes] = []
    zoom = dpi / 72.0  # PyMuPDF 默认 72 DPI
    mat = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def detect_is_answer_sheet(filename: str, first_page_text: Optional[str] = None) -> bool:
    """
    根据文件名关键词或首页识别内容，判断是否为答案卷。

    Args:
        filename: PDF 文件名（不含路径）。
        first_page_text: 首页识别出的文字（可选）。

    Returns:
        True 表示答案卷，False 表示试题卷。
    """
    answer_keywords = ["答案", "解析", "参考答案", "answer", "solution", "解答"]
    name_lower = filename.lower()
    for kw in answer_keywords:
        if kw in name_lower:
            return True
    if first_page_text:
        head = first_page_text[:300].lower()
        for kw in answer_keywords:
            if kw in head:
                return True
    return False


def _extract_year_from_filename(filename: str) -> Optional[int]:
    """从文件名中提取年份（四位数字）。"""
    match = re.search(r"(\d{4})", filename)
    return int(match.group(1)) if match else None


def _extract_course_name(filename: str) -> Optional[str]:
    """
    尝试从文件名提取课程名称。
    文件名格式通常为：2021-课程名-期末.pdf 或 课程名2022春.pdf 或 1617期末带答案.pdf
    """
    # 去掉扩展名
    name = os.path.splitext(filename)[0]
    # 去掉常见标识词
    for kw in ["期末", "期中", "考试", "试题", "答案", "解析", "春", "秋", "带", "Final", "Midterm", "副本"]:
        name = name.replace(kw, "")
    # 去掉四位数字（年份/学年）
    name = re.sub(r"\d{4}", "", name)
    # 去掉连字符、下划线和多余空格
    name = re.sub(r"[-_\s]+", " ", name).strip()
    return name if name else None


async def recognize_page(
    image_bytes: bytes, page_num: int, total_pages: int
) -> dict:
    """
    将单页图片发送给 Qwen-VL-Max 进行识别，返回结构化字典。

    Args:
        image_bytes: 页面 PNG 字节数据。
        page_num: 当前页码（1-indexed）。
        total_pages: 总页数。

    Returns:
        dict，schema 见 _PAGE_PROMPT 中的 JSON schema。
    """
    is_last = page_num == total_pages
    last_hint = _LAST_PAGE_HINT if is_last else ""
    prompt = _PAGE_PROMPT.format(
        page_num=page_num,
        total_pages=total_pages,
        last_page_hint=last_hint,
    )

    raw_text = await call_vision_model(image_bytes, prompt)

    # 尝试从返回文本中提取 JSON
    page_data = _parse_json_from_text(raw_text)
    if page_data is None:
        logger.warning("第 %d 页 JSON 解析失败，返回空结果。原始内容: %s", page_num, raw_text)
        page_data = {
            "page_questions": [],
            "section_title": None,
            "is_answer_page": False,
        }
    return page_data


_JSON_VALID_ESCAPES = set('"\\\/bfnrtu')


def _fix_latex_escapes(text: str) -> str:
    """将 LaTeX 单反斜杠（非法 JSON 转义）修复为双反斜杠，保留合法 JSON 转义。"""
    result: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            next_ch = text[i + 1]
            if next_ch in _JSON_VALID_ESCAPES:
                result.append(ch)
                result.append(next_ch)
            else:
                result.append('\\')
                result.append('\\')
                result.append(next_ch)
            i += 2
        else:
            result.append(ch)
            i += 1
    return ''.join(result)


def _try_parse(raw: str) -> Optional[dict]:
    """先直接解析，失败时修复 LaTeX 反斜杠后再解析。"""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_fix_latex_escapes(raw))
    except json.JSONDecodeError:
        return None


def _parse_json_from_text(text: str) -> Optional[dict]:
    """
    从模型输出的文本中提取第一个有效 JSON 对象。
    兼容以下情况：
      1. 纯 JSON 文本
      2. ```json ... ``` 代码块包裹
      3. 其他前缀/后缀文字 + { ... } 括号计数兜底
    每种路径都先尝试直接解析，失败再用 _fix_latex_escapes 修复单反斜杠后重试。
    """
    text = text.strip()

    # 1. 直接解析（含 LaTeX 修复兜底）
    result = _try_parse(text)
    if result is not None:
        return result

    # 2. 提取 ```json ... ``` 代码块
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block:
        result = _try_parse(code_block.group(1).strip())
        if result is not None:
            return result

    # 3. 括号计数兜底（处理无代码块的边缘情况）
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    end = -1
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None
    return _try_parse(text[start : end + 1])


def _merge_pages(page_results: list[dict]) -> list[dict]:
    """
    将多页识别结果合并为一份试卷的题目列表。

    相同题号的跨页题目拼接 content，其余字段保留首次出现的值。
    """
    merged: dict[str, dict] = {}
    order: list[str] = []

    for page_data in page_results:
        for q in page_data.get("page_questions", []):
            num = str(q.get("number", "")).strip()
            if not num:
                continue
            if num not in merged:
                merged[num] = {
                    "number": num,
                    "type": q.get("type"),
                    "points": q.get("points"),
                    "content": q.get("content", ""),
                    "figure_descriptions": q.get("figure_descriptions", []),
                    "answer": q.get("answer"),
                    "scoring_criteria": q.get("scoring_criteria"),
                }
                order.append(num)
            else:
                # 跨页续接内容
                existing = merged[num]
                extra = q.get("content", "")
                if extra:
                    existing["content"] = existing["content"].rstrip() + "\n" + extra
                # 合并图描述
                existing["figure_descriptions"].extend(q.get("figure_descriptions", []))
                # 答案优先保留
                if not existing["answer"] and q.get("answer"):
                    existing["answer"] = q["answer"]
                if not existing["scoring_criteria"] and q.get("scoring_criteria"):
                    existing["scoring_criteria"] = q["scoring_criteria"]
                # 类型和分值只在未知时补充
                if not existing["type"] and q.get("type"):
                    existing["type"] = q["type"]
                if existing["points"] is None and q.get("points") is not None:
                    existing["points"] = q["points"]

    return [merged[n] for n in order]


async def parse_single_pdf(
    pdf_path: str,
    progress_callback=None,
) -> dict:
    """
    解析单份 PDF，返回结构化试卷数据。

    Args:
        pdf_path: PDF 文件绝对路径。
        progress_callback: 可选的进度回调 async def callback(current_page, total_pages)。

    Returns:
        dict，结构见 ExamState.parsed_exams 的注释。
    """
    filename = os.path.basename(pdf_path)
    logger.info("开始解析 PDF: %s", filename)

    # 渲染所有页面
    images = render_pdf_to_images(pdf_path)
    total_pages = len(images)
    logger.info("PDF 共 %d 页", total_pages)

    # 逐页识别（全并发；以下信号量限流已注释以提速，可能触发 NewAPI 限速）
    # local_sem = asyncio.Semaphore(3)  # 单 PDF 内最多 N 页同时请求
    # global_sem 见 agent1_parse_pdfs 中 vision_sem

    async def recognize_with_sem(idx: int, img: bytes) -> dict:
        # async with local_sem:
        #     if global_sem is not None:
        #         async with global_sem:
        #             result = await recognize_page(img, idx + 1, total_pages)
        #     else:
        #         result = await recognize_page(img, idx + 1, total_pages)
        result = await recognize_page(img, idx + 1, total_pages)
        if progress_callback:
            await progress_callback(idx + 1, total_pages)
        return result

    tasks = [recognize_with_sem(i, img) for i, img in enumerate(images)]
    page_results: list[dict] = await asyncio.gather(*tasks)

    # 合并多页
    raw_questions = _merge_pages(page_results)

    year = _extract_year_from_filename(filename)
    course = _extract_course_name(filename)

    logger.info("PDF %s 解析完成：%d 道题", filename, len(raw_questions))

    return {
        "filename": filename,
        "year": year,
        "course_name": course,
        "is_answer_sheet": False,
        "raw_questions": raw_questions,
    }


async def agent1_parse_pdfs(state: ExamState) -> dict:
    """
    LangGraph 节点入口函数。

    并发解析所有 PDF（每个 PDF 内部页面也并发），将结果写入
    state["parsed_exams"]，并更新 parse_status 为 "done" 或 "error"。
    """
    pdf_paths: list[str] = state.get("pdf_paths", [])
    if not pdf_paths:
        logger.warning("agent1_parse_pdfs: pdf_paths 为空，跳过。")
        return {"parsed_exams": [], "parse_status": "done"}

    logger.info("并发解析 %d 份 PDF...", len(pdf_paths))

    # 全局信号量：跨 PDF 最多 N 个并发视觉请求（已注释以提速）
    # vision_sem = asyncio.Semaphore(3)

    async def _safe_parse(pdf_path: str):
        """解析单份 PDF，失败返回 Exception 而非抛出。"""
        try:
            return await parse_single_pdf(pdf_path)
        except Exception as exc:
            logger.exception("解析 %s 时出错: %s", pdf_path, exc)
            return exc

    results = await asyncio.gather(*[_safe_parse(p) for p in pdf_paths])

    parsed_exams: list[dict] = []
    errors: list[str] = []
    for pdf_path, result in zip(pdf_paths, results):
        if isinstance(result, Exception):
            errors.append(f"{os.path.basename(pdf_path)}: {str(result)}")
        else:
            parsed_exams.append(result)

    status = "done" if not errors else "error"
    update: dict = {
        "parsed_exams": parsed_exams,
        "parse_status": status,
    }
    if errors:
        update["parse_progress"] = {"errors": errors}
    return update
