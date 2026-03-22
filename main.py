"""
InterviewPilot - 智能面试准备助手
项目入口
"""
import sys
from pathlib import Path

# 设置控制台输出编码为 UTF-8（Windows 兼容）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保项目根目录在 Python 路径中
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))


def check_dependencies():
    """检查依赖"""
    missing = []
    
    try:
        import streamlit
    except ImportError:
        missing.append("streamlit")
    
    try:
        import openai
    except ImportError:
        missing.append("openai")
    
    try:
        import langgraph
    except ImportError:
        missing.append("langgraph")
    
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        missing.append("qdrant-client")
    
    if missing:
        print("❌ 缺少依赖，请运行：")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True


def check_env():
    """检查环境变量"""
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    provider = os.getenv("LLM_PROVIDER", "qwen")
    key_name = f"{provider.upper()}_API_KEY"
    api_key = os.getenv(key_name, "")
    
    if not api_key:
        print(f"❌ 未设置 {key_name}")
        print("   请在 .env 文件中配置 API Key")
        return False
    
    print(f"✅ 使用 LLM: {provider}")
    return True


def run_cli():
    """命令行模式"""
    from agent import run_agent
    
    print("=" * 50)
    print("🚀 InterviewPilot - 命令行模式")
    print("=" * 50)
    print("输入 'quit' 退出")
    print("试试：「考考我」「讲讲 Redis」「今天学什么」")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("再见！")
                break
            
            response = run_agent(user_input)
            print(f"\n助手: {response}")
        
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


def run_web():
    """Web 模式（Streamlit）"""
    import subprocess
    import os
    
    app_path = ROOT_DIR / "ui" / "app.py"
    
    print("🚀 启动 Web 界面...")
    print("   访问 http://localhost:8501")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port=8501",
        "--server.headless=true"
    ])


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="InterviewPilot - 智能面试准备助手")
    parser.add_argument(
        "--mode", "-m",
        choices=["web", "cli"],
        default="web",
        help="运行模式: web(默认) 或 cli"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="跳过依赖检查"
    )
    
    args = parser.parse_args()
    
    print("🚀 InterviewPilot 启动中...")
    
    # 检查
    if not args.skip_check:
        if not check_dependencies():
            return
        if not check_env():
            return
    
    # 创建数据目录
    data_dir = ROOT_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "raw").mkdir(exist_ok=True)
    
    # 运行
    if args.mode == "cli":
        run_cli()
    else:
        run_web()


if __name__ == "__main__":
    main()
