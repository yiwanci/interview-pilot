class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def mock_all(self, mocker):
        """Mock 所有外部依赖"""
        # Mock LLM
        mock_llm_response = Mock()
        mock_llm_response.choices = [Mock(message=Mock(content="这是今日学习计划"))]
        
        mock_openai_instance = Mock()
        mock_openai_instance.chat.completions.create.return_value = mock_llm_response
        
        mocker.patch('agent.nodes.study_node.OpenAI', return_value=mock_openai_instance)
        mocker.patch('agent.nodes.router_node.OpenAI', return_value=mock_openai_instance)
        mocker.patch('agent.nodes.interview_node.OpenAI', return_value=mock_openai_instance)
        mocker.patch('agent.nodes.plan_node.OpenAI', return_value=mock_openai_instance)
        mocker.patch('agent.nodes.crawler_node.OpenAI', return_value=mock_openai_instance)
        mocker.patch('agent.nodes.chat_node.OpenAI', return_value=mock_openai_instance)
        
        # Mock MemoryManager
        mock_mm = Mock()
        mock_mm.format_context_for_prompt.return_value = "测试上下文"
        mock_mm.get_today_plan.return_value = {
            "due_reviews": [],
            "weak_points": [],
            "summary": "暂无待复习内容"
        }
        
        # Mock db
        mock_db = Mock()
        mock_db.get_full_profile.return_value = Mock(
            target_positions=["Java后端"],
            target_companies=["字节"],
            tech_stack=["Java"],
        )
        mock_db.get_stats.return_value = {
            "total_knowledge_points": 10,
            "mastered_count": 5,
            "due_review_count": 2,
            "total_study_logs": 20,
        }
        mock_mm.db = mock_db
        
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
        assert len(result["response"]) > 0
