import os
import shutil
import stat

def setup_hooks():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, '..')
    
    # Paths
    hook_src = os.path.join(current_dir, 'pre-commit')
    git_dir = os.path.join(project_root, '.git')
    
    if not os.path.exists(git_dir):
        print("Error: .git directory not found. Please run this script from within the git repository.")
        return
        
    hooks_dir = os.path.join(git_dir, 'hooks')
    os.makedirs(hooks_dir, exist_ok=True)
    
    hook_dest = os.path.join(hooks_dir, 'pre-commit')
    
    # Copy the hook file
    shutil.copy2(hook_src, hook_dest)
    print(f"Copied hook to {hook_dest}")
    
    # Make the hook executable (non-Windows)
    if os.name != 'nt':
        st = os.stat(hook_dest)
        os.chmod(hook_dest, st.st_mode | stat.S_IEXEC)
        print("Set hook as executable.")
        
    print("Git hooks configured successfully!")

if __name__ == "__main__":
    setup_hooks()
