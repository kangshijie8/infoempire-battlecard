"""
发布模块 - 多平台发布
"""

from typing import Dict
from datetime import datetime
from pathlib import Path

class ChainContentPublisher:
    """
    产业链内容发布器
    （注意：这是产业链特定实现，与 core.content_pipeline.ContentPublisher 区分）
    """
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.platforms = ["markdown", "html", "json"]
    
    def publish_markdown(self, content: str, filename: str = None) -> str:
        """
        发布为Markdown
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"content_{timestamp}.md"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(filepath)
    
    def publish_json(self, data: Dict, filename: str = None) -> str:
        """
        发布为JSON
        """
        import json
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def publish(self, content: str, data: Dict = None, format: str = "markdown") -> Dict:
        """
        统一发布接口
        """
        result = {
            "success": False,
            "files": [],
            "errors": []
        }
        
        try:
            if format == "markdown":
                filepath = self.publish_markdown(content)
                result["files"].append(filepath)
            elif format == "json":
                filepath = self.publish_json(data or {})
                result["files"].append(filepath)
            elif format == "all":
                md_path = self.publish_markdown(content)
                json_path = self.publish_json(data or {})
                result["files"].extend([md_path, json_path])
            
            result["success"] = True
            
        except Exception as e:
            result["errors"].append(str(e))
        
        return result


# 为了向后兼容，保留别名
ContentPublisher = ChainContentPublisher


# 测试
if __name__ == "__main__":
    publisher = ChainContentPublisher()
    
    test_content = "# 测试内容\n\n这是测试发布的内容。"
    test_data = {"title": "测试", "content": test_content}
    
    result = publisher.publish(test_content, test_data, format="all")
    
    print("="*60)
    print("📤 发布测试")
    print("="*60)
    print(f"成功: {result['success']}")
    print(f"文件: {result['files']}")
