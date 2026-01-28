"""Git 操作脚本 - 用于推送到 GitHub"""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def run_git(args, check=True):
    """运行 Git 命令"""
    result = subprocess.run(['git'] + args, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        print(f"Git command failed: git {' '.join(args)}")
        return False
    return True

def main():
    print("=" * 60)
    print("PolyMind MCP - Git 推送脚本")
    print("=" * 60)
    
    # 1. 检查状态
    print("\n📋 检查 Git 状态...")
    run_git(['status'], check=False)
    
    # 2. 检查 .env 是否被追踪
    result = subprocess.run(['git', 'ls-files', '.env'], capture_output=True, text=True)
    if result.stdout.strip():
        print("\n⚠️  警告: .env 文件正在被追踪!")
        print("   运行: git rm --cached .env")
        run_git(['rm', '--cached', '.env'], check=False)
    else:
        print("\n✅ .env 未被追踪（安全）")
    
    # 3. 检查根目录的 polymarket.db
    result = subprocess.run(['git', 'ls-files', 'polymarket.db'], capture_output=True, text=True)
    if result.stdout.strip():
        print("\n⚠️  警告: polymarket.db 正在被追踪!")
        run_git(['rm', '--cached', 'polymarket.db'], check=False)
    
    # 4. 添加所有更改
    print("\n📦 添加更改...")
    run_git(['add', '-A'])
    
    # 5. 显示将要提交的文件
    print("\n📝 将要提交的文件:")
    run_git(['status', '--short'], check=False)
    
    # 6. 提交
    print("\n💾 创建提交...")
    commit_msg = "feat: 完善项目功能，修复 CSS 兼容性，添加安装指南"
    run_git(['commit', '-m', commit_msg], check=False)
    
    # 7. 检查远程仓库
    print("\n🔗 检查远程仓库...")
    result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
        
        # 8. 推送
        print("\n🚀 推送到 GitHub...")
        run_git(['push', '-u', 'origin', 'main'], check=False)
        # 如果 main 分支不存在，尝试 master
        run_git(['push', '-u', 'origin', 'master'], check=False)
    else:
        print("❌ 未配置远程仓库!")
        print("\n请先添加远程仓库:")
        print("  git remote add origin https://github.com/YOUR_USERNAME/poly-mind-mcp.git")
        print("  然后重新运行此脚本")
    
    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
