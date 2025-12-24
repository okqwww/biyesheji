# -*- coding: utf-8 -*-
"""
知识图谱数据导入脚本
将JSON格式的课程知识图谱数据导入Neo4j数据库
"""

import json
from neo4j import GraphDatabase

# Neo4j连接配置 - 请根据实际情况修改
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "211BUPTzyj")


def clear_database(driver):
    """清空数据库"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("✓ 数据库已清空")


def import_course(driver, course_data):
    """导入课程数据"""
    with driver.session() as session:
        # 创建课程节点
        course = course_data["course"]
        session.run("""
            CREATE (c:Course {
                id: $id,
                name: $name,
                description: $description
            })
        """, **course)
        print(f"\n✓ 已创建课程: {course['name']}")
        
        # 创建章节和知识点
        for chapter in course_data["chapters"]:
            # 创建章节节点
            session.run("""
                CREATE (ch:Chapter {
                    id: $id,
                    name: $name,
                    order: $order
                })
            """, id=chapter["id"], name=chapter["name"], order=chapter["order"])
            
            # 创建课程到章节的关系
            session.run("""
                MATCH (c:Course {id: $course_id})
                MATCH (ch:Chapter {id: $chapter_id})
                CREATE (c)-[:HAS_CHAPTER]->(ch)
            """, course_id=course["id"], chapter_id=chapter["id"])
            
            # 创建知识点
            for kp in chapter["knowledge_points"]:
                session.run("""
                    CREATE (kp:KnowledgePoint {
                        id: $id,
                        name: $name,
                        description: $description,
                        keywords: $keywords
                    })
                """, **kp)
                
                # 创建章节到知识点的关系
                session.run("""
                    MATCH (ch:Chapter {id: $chapter_id})
                    MATCH (kp:KnowledgePoint {id: $kp_id})
                    CREATE (ch)-[:CONTAINS]->(kp)
                """, chapter_id=chapter["id"], kp_id=kp["id"])
            
            print(f"  ├── 章节: {chapter['name']} ({len(chapter['knowledge_points'])}个知识点)")
        
        # 创建知识点之间的关联关系
        relations_count = 0
        for relation in course_data.get("relations", []):
            result = session.run("""
                MATCH (kp1:KnowledgePoint {id: $source})
                MATCH (kp2:KnowledgePoint {id: $target})
                CREATE (kp1)-[:RELATES_TO]->(kp2)
                RETURN kp1, kp2
            """, source=relation["source"], target=relation["target"])
            if result.single():
                relations_count += 1
        
        print(f"  └── 已创建 {relations_count} 个知识点关联关系")


def count_nodes(driver):
    """统计节点数量"""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Course) WITH count(c) as courses
            MATCH (ch:Chapter) WITH courses, count(ch) as chapters
            MATCH (kp:KnowledgePoint) WITH courses, chapters, count(kp) as knowledge_points
            MATCH ()-[r:RELATES_TO]->() WITH courses, chapters, knowledge_points, count(r) as relations
            RETURN courses, chapters, knowledge_points, relations
        """)
        record = result.single()
        print("\n" + "="*40)
        print("数据统计")
        print("="*40)
        print(f"  课程数量:     {record['courses']}")
        print(f"  章节数量:     {record['chapters']}")
        print(f"  知识点数量:   {record['knowledge_points']}")
        print(f"  关联关系数量: {record['relations']}")
        print("="*40)


def main():
    print("="*40)
    print("知识图谱数据导入工具")
    print("="*40)
    
    # 连接Neo4j
    print(f"\n正在连接 Neo4j ({URI})...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        # 验证连接
        driver.verify_connectivity()
        print("✓ Neo4j连接成功!")
        
        # 清空数据库
        print("\n正在清空数据库...")
        clear_database(driver)
        
        # 导入Python编程基础
        print("\n" + "-"*40)
        print("导入课程: Python编程基础")
        print("-"*40)
        with open("G:/biyesheji/data/python_basics.json", "r", encoding="utf-8") as f:
            python_data = json.load(f)
        import_course(driver, python_data)
        
        # 导入Web全栈开发
        print("\n" + "-"*40)
        print("导入课程: Web全栈开发")
        print("-"*40)
        with open("G:/biyesheji/data/web_fullstack.json", "r", encoding="utf-8") as f:
            web_data = json.load(f)
        import_course(driver, web_data)
        
        # 统计结果
        count_nodes(driver)
        
        print("\n✓ 数据导入完成!")
        print("\n提示: 打开 http://localhost:7474 查看知识图谱")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        print("\n请检查:")
        print("  1. Neo4j是否已启动")
        print("  2. 连接地址和密码是否正确")
        print("  3. 是否已安装neo4j包 (pip install neo4j)")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
