# Neo4j 部署与数据导入指南

## 一、Neo4j 安装

### 方式一：Docker安装（推荐）

Docker方式简单快捷，易于管理和迁移。

#### 1. 安装Docker Desktop

1. 访问 [Docker官网](https://www.docker.com/products/docker-desktop/) 下载 Docker Desktop for Windows
2. 运行安装程序，按提示完成安装
3. 安装完成后重启电脑
4. 启动 Docker Desktop，等待其完全启动

#### 2. 拉取Neo4j镜像并启动

打开 PowerShell 或命令提示符，执行以下命令：

```powershell
# 创建数据持久化目录
mkdir G:\biyesheji\neo4j\data
mkdir G:\biyesheji\neo4j\logs
mkdir G:\biyesheji\neo4j\import

# 启动Neo4j容器
docker run -d ^
  --name neo4j ^
  -p 7474:7474 ^
  -p 7687:7687 ^
  -v G:\biyesheji\neo4j\data:/data ^
  -v G:\biyesheji\neo4j\logs:/logs ^
  -v G:\biyesheji\neo4j\import:/var/lib/neo4j/import ^
  -e NEO4J_AUTH=neo4j/password123 ^
  neo4j:5.15.0
```

**参数说明**：
- `-p 7474:7474`：Web管理界面端口
- `-p 7687:7687`：Bolt协议端口（程序连接用）
- `-v`：数据卷挂载，保证数据持久化
- `-e NEO4J_AUTH=neo4j/password123`：设置用户名和密码

#### 3. 验证安装

```powershell
# 查看容器状态
docker ps

# 查看日志
docker logs neo4j
```

打开浏览器访问 http://localhost:7474

- 用户名：`neo4j`
- 密码：`password123`

### 方式二：直接安装

#### 1. 下载Neo4j

访问 [Neo4j下载页面](https://neo4j.com/download-center/#community) 下载 Neo4j Community Edition

#### 2. 安装Java

Neo4j需要Java 17+，下载安装 [Eclipse Temurin JDK 17](https://adoptium.net/)

#### 3. 解压并配置

1. 解压下载的Neo4j压缩包到 `G:\biyesheji\neo4j-community`
2. 设置环境变量 `NEO4J_HOME` 为解压目录
3. 将 `%NEO4J_HOME%\bin` 添加到 PATH

#### 4. 启动Neo4j

```powershell
# 以控制台模式启动
neo4j console

# 或安装为Windows服务
neo4j install-service
neo4j start
```

---

## 二、Neo4j 基本操作

### 2.1 Web管理界面

访问 http://localhost:7474 进入Neo4j Browser

**常用操作**：
- 左侧可查看数据库信息、节点标签、关系类型
- 顶部输入框可执行Cypher查询
- 查询结果可以图形化或表格形式展示

### 2.2 Cypher基础语法

```cypher
-- 创建节点
CREATE (n:Course {id: 'python', name: 'Python编程基础'})

-- 查询所有节点
MATCH (n) RETURN n

-- 查询特定标签的节点
MATCH (c:Course) RETURN c

-- 创建关系
MATCH (c:Course {id: 'python'}), (ch:Chapter {id: 'ch01'})
CREATE (c)-[:HAS_CHAPTER]->(ch)

-- 删除所有数据（谨慎使用！）
MATCH (n) DETACH DELETE n
```

---

## 三、数据导入

### 3.1 创建导入脚本

在项目目录下创建数据导入Python脚本：

```python
# G:\biyesheji\scripts\import_knowledge_graph.py

import json
from neo4j import GraphDatabase

# Neo4j连接配置
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

def clear_database(driver):
    """清空数据库"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("数据库已清空")

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
        print(f"已创建课程: {course['name']}")
        
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
            
            print(f"  已创建章节: {chapter['name']} ({len(chapter['knowledge_points'])}个知识点)")
        
        # 创建知识点之间的关联关系
        for relation in course_data.get("relations", []):
            session.run("""
                MATCH (kp1:KnowledgePoint {id: $source})
                MATCH (kp2:KnowledgePoint {id: $target})
                CREATE (kp1)-[:RELATES_TO]->(kp2)
            """, source=relation["source"], target=relation["target"])
        
        print(f"  已创建 {len(course_data.get('relations', []))} 个知识点关联关系")

def count_nodes(driver):
    """统计节点数量"""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Course) WITH count(c) as courses
            MATCH (ch:Chapter) WITH courses, count(ch) as chapters
            MATCH (kp:KnowledgePoint) WITH courses, chapters, count(kp) as knowledge_points
            RETURN courses, chapters, knowledge_points
        """)
        record = result.single()
        print("\n=== 数据统计 ===")
        print(f"课程数量: {record['courses']}")
        print(f"章节数量: {record['chapters']}")
        print(f"知识点数量: {record['knowledge_points']}")

def main():
    # 连接Neo4j
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    try:
        # 验证连接
        driver.verify_connectivity()
        print("Neo4j连接成功!\n")
        
        # 清空数据库
        clear_database(driver)
        
        # 导入Python编程基础
        print("\n开始导入: Python编程基础")
        with open("G:/biyesheji/data/python_basics.json", "r", encoding="utf-8") as f:
            python_data = json.load(f)
        import_course(driver, python_data)
        
        # 导入Web全栈开发
        print("\n开始导入: Web全栈开发")
        with open("G:/biyesheji/data/web_fullstack.json", "r", encoding="utf-8") as f:
            web_data = json.load(f)
        import_course(driver, web_data)
        
        # 统计结果
        count_nodes(driver)
        
        print("\n数据导入完成!")
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
```

### 3.2 安装Python依赖

```powershell
pip install neo4j
```

### 3.3 运行导入脚本

```powershell
cd G:\biyesheji
python scripts/import_knowledge_graph.py
```

**预期输出**：
```
Neo4j连接成功!

数据库已清空

开始导入: Python编程基础
已创建课程: Python编程基础
  已创建章节: Python环境与基础语法 (5个知识点)
  已创建章节: 数据类型 (8个知识点)
  ...
  已创建 32 个知识点关联关系

开始导入: Web全栈开发
已创建课程: Web全栈开发
  已创建章节: HTML基础 (8个知识点)
  ...
  已创建 42 个知识点关联关系

=== 数据统计 ===
课程数量: 2
章节数量: 21
知识点数量: 89

数据导入完成!
```

---

## 四、验证数据

### 4.1 在Neo4j Browser中查询

打开 http://localhost:7474 执行以下查询：

```cypher
-- 查看所有课程
MATCH (c:Course) RETURN c

-- 查看Python课程的完整结构
MATCH (c:Course {id: 'python_basics'})-[:HAS_CHAPTER]->(ch:Chapter)-[:CONTAINS]->(kp:KnowledgePoint)
RETURN c, ch, kp

-- 查看知识点之间的关联
MATCH (kp1:KnowledgePoint)-[:RELATES_TO]->(kp2:KnowledgePoint)
RETURN kp1.name, kp2.name LIMIT 20

-- 统计每个章节的知识点数量
MATCH (ch:Chapter)-[:CONTAINS]->(kp:KnowledgePoint)
RETURN ch.name as chapter, count(kp) as knowledge_point_count
ORDER BY ch.order
```

### 4.2 可视化查看

在Neo4j Browser中执行以下查询，可以看到图形化的知识图谱：

```cypher
-- 查看某个课程的完整图谱（限制节点数量避免太乱）
MATCH path = (c:Course {id: 'python_basics'})-[:HAS_CHAPTER]->(ch:Chapter)-[:CONTAINS]->(kp:KnowledgePoint)
RETURN path LIMIT 50
```

---

## 五、常用运维命令

### Docker方式

```powershell
# 停止Neo4j
docker stop neo4j

# 启动Neo4j
docker start neo4j

# 重启Neo4j
docker restart neo4j

# 查看日志
docker logs -f neo4j

# 删除容器（数据保留在挂载目录）
docker rm neo4j

# 进入容器内部
docker exec -it neo4j bash
```

### 直接安装方式

```powershell
# 启动
neo4j start

# 停止
neo4j stop

# 重启
neo4j restart

# 查看状态
neo4j status
```

---

## 六、常见问题

### Q1: 连接被拒绝

**原因**：Neo4j服务未启动或端口被占用

**解决**：
```powershell
# 检查Docker容器状态
docker ps -a

# 如果容器已停止，启动它
docker start neo4j

# 检查端口占用
netstat -ano | findstr :7687
```

### Q2: 认证失败

**原因**：密码不正确

**解决**：
- 确认使用的密码是启动时设置的密码
- Docker方式可以删除容器重新创建

### Q3: 导入脚本报错 "neo4j module not found"

**解决**：
```powershell
pip install neo4j
```

### Q4: 中文显示乱码

**解决**：确保JSON文件使用UTF-8编码保存，脚本中指定 `encoding="utf-8"`

---

## 七、项目中使用Neo4j

### Python后端连接示例

```python
# backend/app/db/neo4j.py

from neo4j import GraphDatabase
from app.core.config import settings

class Neo4jConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    def close(self):
        self.driver.close()
    
    def get_courses(self):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Course)
                OPTIONAL MATCH (c)-[:HAS_CHAPTER]->(:Chapter)-[:CONTAINS]->(kp:KnowledgePoint)
                RETURN c.id as id, c.name as name, c.description as description,
                       count(kp) as knowledge_point_count
            """)
            return [dict(record) for record in result]
    
    def get_course_graph(self, course_id: str):
        with self.driver.session() as session:
            # 获取节点
            nodes_result = session.run("""
                MATCH (c:Course {id: $course_id})-[:HAS_CHAPTER]->(ch:Chapter)-[:CONTAINS]->(kp:KnowledgePoint)
                WITH collect({id: ch.id, name: ch.name, type: 'chapter'}) as chapters,
                     collect({id: kp.id, name: kp.name, type: 'knowledge_point', description: kp.description}) as kps
                RETURN chapters + kps as nodes
            """, course_id=course_id)
            
            # 获取边
            edges_result = session.run("""
                MATCH (c:Course {id: $course_id})-[:HAS_CHAPTER]->(ch:Chapter)-[:CONTAINS]->(kp:KnowledgePoint)
                WITH collect({source: ch.id, target: kp.id, type: 'contains'}) as contains_edges
                MATCH (kp1:KnowledgePoint)-[:RELATES_TO]->(kp2:KnowledgePoint)
                WHERE exists((c)-[:HAS_CHAPTER]->(:Chapter)-[:CONTAINS]->(kp1))
                WITH contains_edges, collect({source: kp1.id, target: kp2.id, type: 'relates_to'}) as relates_edges
                RETURN contains_edges + relates_edges as edges
            """, course_id=course_id)
            
            nodes = nodes_result.single()["nodes"]
            edges = edges_result.single()["edges"]
            
            return {"nodes": nodes, "edges": edges}

# 使用示例
neo4j = Neo4jConnection()
courses = neo4j.get_courses()
graph = neo4j.get_course_graph("python_basics")
```

---

## 八、下一步

完成Neo4j部署和数据导入后，可以继续：

1. **后端开发**：创建FastAPI项目，实现API接口
2. **前端开发**：创建Vue 3项目，实现知识图谱可视化
3. **大模型对接**：配置DeepSeek API，实现题目生成

如需帮助，请继续提问！
