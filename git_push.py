import os
import subprocess
from datetime import datetime

def git_push_with_timestamp():
    """
    Push changes to the Git repository with a commit message that includes the current date and time.
    Sets upstream if it's the first push to the specified branch.
    """
    # Use the current working directory
    repo_path = os.getcwd()
    os.chdir(repo_path)
    
    now = datetime.now()
    commit_message = now.strftime("Update on %Y-%m-%d at %H:%M:%S")
    
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        subprocess.run(['git', 'push', '--set-upstream', 'origin', 'main'], check=True)
        
        print(f"Successfully pushed with commit: '{commit_message}'")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    git_push_with_timestamp()  # Call the function directly