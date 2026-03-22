"""
Agent 系统测试
"""
import pytest
from unittest.mock import Mock, patch

from agent import AgentState, run_agent
from agent.nodes import RouterNode


class TestRouterNode:
    """路由节点测试"""
    
    @pytest.fixture
    def router(self, mocker):
        """Mock LLM"""
        mocker.patch('agent.nodes.router_node.OpenAI')
        return RouterNode()
    
    def test_quick_match_study(self, router):
        """快速匹配 - 学习意图"""
        assert router._quick_match("讲讲 Redis") == "study"
        assert router._quick_match("什么是 JVM") == "study"
        assert router._quick_match("介绍一下 Spring") == "study"
        assert router._quick_match("HashMap 原理是什么") == "study"
    
    def test_quick_match_interview(self, router):
        """快速匹配 - 面试意图"""
        assert router._quick_match("考考我") == "interview"
        assert router._quick_match("来道题") == "interview"
        assert router._quick_match("模拟面试") == "interview"
        assert router._quick_match("出题测试一下") == "interview"
    
    def test_quick_match_crawl(self, router):
        """快速匹配 - 爬取意图"""
        assert router._quick_match("搜集面经") == "crawl"
        assert router._quick_match("爬取小红书") == "crawl"
        assert router._quick_match("导入数据") == "crawl"
        assert router._quick_match("应该是什么类型的JSON") == "crawl"
    
    def test_quick_match_plan(self, router):
        """快速匹配 - 计划意图"""
        assert router._quick_match("今天学什么") == "plan"
        assert router._quick_match("学习计划") == "plan"
        assert router._quick_match("查看进度") == "plan"
        assert router._quick_match("周报") == "plan"
    
    def test_quick_match_none(self, router):
        """快速匹配 - 无法匹配"""
        assert router._quick_match("你好") == ""
        assert router._quick_match("谢谢") == ""
    
    def test_router_node_call(self, router):
        """路由节点调用"""
        state = AgentState(user_input="讲讲 Redis")
        
        result = router(state)
        
        assert result["intent"] == "study"


class TestAgentState:
    """Agent 状态测试"""
    
    def test_state_creation(self):
        """状态创建"""
        state = AgentState(
            user_input="测试输入",
            intent="study",
        )
        
        assert state["user_input"] == "测试输入"
        assert state["intent"] == "study"
    
    def test_state_optional_fields(self):
        """可选字段"""
        state = AgentState(user_input="测试")
        
        # 可选字段应该可以不存在
        assert state.get("memory_context") is None
        assert state.get("response") is None


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def mock_all(self, mocker):
        """Mock 所有外部依赖"""
        # Mock LLM
        mock_llm_response = Mock()
        mock_llm_response.choices = [Mock(message=Mock(content="测试回复"))]
        
        mock_openai = mocker.patch('agent.nodes.study_node.OpenAI')
        mock_openai.return_value.chat.completions.create.return_value = mock_llm_response
        
        mocker.patch('agent.nodes.router_node.OpenAI')
        mocker.patch('agent.nodes.interview_node.OpenAI')
        mocker.patch('agent.nodes.plan_node.OpenAI')
        mocker.patch('agent.nodes.crawler_node.OpenAI')
        mocker.patch('agent.nodes.chat_node.OpenAI')
        
        # Mock MemoryManager
        mock_mm = Mock()
        mock_mm.format_context_for_prompt.return_value = "测试上下文"
        mock_mm.get_today_plan.return_value = {
            "due_reviews": [],
            "weak_points": [],
            "summary": "暂无待复习内容"
        }
        mocker.patch('agent.nodes.study_node.MemoryManager', return_value=mock_mm)
        mocker.patch('agent.nodes.interview_node.MemoryManager', return_value=mock_mm)
        mocker.patch('agent.nodes.plan_node.MemoryManager', return_value=mock_mm)
        mocker.patch('agent.nodes.chat_node.MemoryManager', return_value=mock_mm)
        
        # Mock RAGPipeline
        mock_rag = Mock()
        mock_rag.query.return_value = {"answer": "RAG回答", "sources": []}
        mock_rag.retrieve.return_value = []
        mocker.patch('agent.nodes.study_node.RAGPipeline', return_value=mock_rag)
        mocker.patch('agent.nodes.interview_node.RAGPipeline', return_value=mock_rag)
    
    def test_study_flow(self, mock_all):
        """学习流程测试"""
        from agent.nodes import study_node
        
        state = AgentState(
            user_input="讲讲 Redis 持久化",
            intent="study",
        )
        
        result = study_node(state)
        
        assert "response" in result
        assert result.get("extracted_topic") is not None
    
    def test_plan_flow(self, mock_all):
        """计划流程测试"""
        from agent.nodes import plan_node
        
        state = AgentState(
            user_input="今天学什么",
            intent="plan",
        )
        
        result = plan_node(state)
        
        assert "response" in result
        assert "计划" in result["response"] or "学习" in result["response"]


class TestCrawlerNode:
    """爬虫节点测试"""
    
    @pytest.fixture
    def crawler_node(self, mocker):
        """Mock 依赖"""
        mocker.patch('agent.nodes.crawler_node.OpenAI')
        mocker.patch('agent.nodes.crawler_node.RAGPipeline')
        mocker.patch('agent.nodes.crawler_node.DataCleaner')
        mocker.patch('agent.nodes.crawler_node.XiaohongshuCrawler')
        mocker.patch('agent.nodes.crawler_node.DouyinCrawler')
        mocker.patch('agent.nodes.crawler_node.LeetCodeCrawler')
        
        from agent.nodes.crawler_node import CrawlerNode
        return CrawlerNode()
    
    def test_quick_parse_xiaohongshu(self, crawler_node):
        """快速解析 - 小红书"""
        result = crawler_node._quick_parse("搜集小红书 Java 面经")
        
        assert result is not None
        assert result["source"] == "xiaohongshu"
        assert "Java" in result["keyword"] or "面经" in result["keyword"]
    
    def test_quick_parse_leetcode(self, crawler_node):
        """快速解析 - LeetCode"""
        result = crawler_node._quick_parse("抓取 LeetCode 字节题目")
        
        assert result is not None
        assert result["source"] == "leetcode"
    
    def test_is_company_query(self, crawler_node):
        """公司查询判断"""
        assert crawler_node._is_company_query("bytedance") == True
        assert crawler_node._is_company_query("字节跳动") == True
        assert crawler_node._is_company_query("阿里巴巴") == True
        assert crawler_node._is_company_query("Java") == False

    def test_is_json_format_question(self, crawler_node):
        assert crawler_node._is_json_format_question("应该是什么类型的JSON") == True


class TestChatNode:
    @pytest.fixture
    def chat_node(self, mocker):
        mocker.patch('agent.nodes.chat_node.OpenAI')
        mock_mm = Mock()
        mock_mm.get_user_name.return_value = ""
        mock_mm.format_context_for_prompt.return_value = "测试上下文"
        mocker.patch('agent.nodes.chat_node.MemoryManager', return_value=mock_mm)
        from agent.nodes.chat_node import ChatNode
        return ChatNode()

    def test_extract_user_name(self, chat_node):
        assert chat_node._extract_user_name("我叫卢鸿涛") == "卢鸿涛"

    def test_chat_store_user_name(self, chat_node):
        state = AgentState(user_input="我叫卢鸿涛", intent="chat")
        result = chat_node(state)
        chat_node.memory_manager.set_user_name.assert_called_once_with("卢鸿涛")
        assert "记住啦" in result["response"]

    def test_chat_query_user_name(self, chat_node):
        chat_node.memory_manager.get_user_name.return_value = "卢鸿涛"
        state = AgentState(user_input="我叫什么名字", intent="chat")
        result = chat_node(state)
        assert "卢鸿涛" in result["response"]


def run_tests():
    """运行测试"""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()
