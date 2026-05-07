# Complete GitHub Setup Guide

This guide will walk you through:
1. Installing Git on Windows
2. Creating a new GitHub repository
3. Pushing your Crawler project to GitHub

## Step 1: Install Git on Windows

1. **Download Git**
   - Go to https://git-scm.com/download/windows
   - Download the latest version (64-bit recommended)

2. **Run the Installer**
   - Double-click the downloaded `.exe` file
   - Click "Next" through the installation
   - Keep default settings (recommended)
   - Complete the installation

3. **Verify Installation**
   - Open Command Prompt or PowerShell
   - Run: `git --version`
   - You should see: `git version X.X.X`

## Step 2: Configure Git with Your Account

Open Command Prompt or PowerShell and run:

```bash
git config --global user.name "Kren Castro"
git config --global user.email "castrokren@gmail.com"
```

Verify it worked:
```bash
git config --global user.name
git config --global user.email
```

## Step 3: Create a New GitHub Repository

1. **Log in to GitHub**
   - Go to https://github.com
   - Log in with your account

2. **Create a New Repository**
   - Click the "+" icon in the top right corner
   - Select "New repository"
   - Fill in the details:
     - **Repository name**: `Crawler`
     - **Description**: `Multi-module PDF Crawler and Classification System`
     - **Public or Private**: Choose based on your preference
     - **Initialize with**: Leave unchecked (we have files already)
   - Click "Create repository"

3. **Copy Your Repository URL**
   - You'll see the new repo page
   - Click the green "Code" button
   - Copy the HTTPS URL (e.g., `https://github.com/castrokren/Crawler.git`)
   - **Save this URL** - you'll need it in the next steps

## Step 4: Set Up Git Locally

1. **Open Command Prompt or PowerShell**
   - Navigate to your project directory:
     ```bash
     cd C:\Projects\Crawler
     ```

2. **Initialize the Repository**
   - Run the batch script I created:
     ```bash
     INIT_GIT_REPO.bat
     ```
   - This will:
     - Initialize Git
     - Stage all your files
     - Create an initial commit

3. **Add GitHub as Remote**
   - Replace the URL with your repo's URL from Step 3:
     ```bash
     git remote add origin https://github.com/castrokren/Crawler.git
     ```
   - Verify it worked:
     ```bash
     git remote -v
     ```
     You should see:
     ```
     origin  https://github.com/castrokren/Crawler.git (fetch)
     origin  https://github.com/castrokren/Crawler.git (push)
     ```

## Step 5: Push to GitHub

In Command Prompt or PowerShell:

```bash
git push -u origin main
```

**First time?** You'll be prompted for authentication:
- Username: Your GitHub username
- Password: Your GitHub personal access token (see below)

### Getting Your Personal Access Token

If you don't have a token:

1. Go to GitHub Settings: https://github.com/settings/tokens
2. Click "Generate new token"
3. Give it a name: "Git CLI"
4. Select scopes: Check "repo" (full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again)
7. Use this token as your password when git asks

### Saving Your Credentials (Optional)

To avoid entering credentials every time:

**Option A: Windows Credential Manager (Recommended)**
- Git automatically stores credentials after first use
- You only enter them once

**Option B: GitHub CLI (More Secure)**
```bash
# Download from https://cli.github.com/
# Install and run:
gh auth login
# Follow the prompts
```

## Step 6: Verify Success

In Command Prompt or PowerShell:

```bash
git log --oneline
git remote -v
```

Then go to your GitHub repository URL (e.g., `https://github.com/castrokren/Crawler`) and refresh - you should see all your files!

## Quick Reference Commands

```bash
# Check status
git status

# See what's on GitHub
git remote -v

# Make changes and push
git add .
git commit -m "Your message"
git push

# Create a new branch for development
git checkout -b feature/consolidate-classify
# Make changes, then:
git push -u origin feature/consolidate-classify

# View commits
git log --oneline
git log --graph --all
```

## Troubleshooting

### "fatal: not a git repository"
- Make sure you're in `C:\Projects\Crawler`
- Run `INIT_GIT_REPO.bat` if you haven't already

### "Authentication failed"
- Check your GitHub username
- Make sure you're using a personal access token (not your password)
- Delete old credentials in Windows Credential Manager if needed

### "remote origin already exists"
- Run: `git remote remove origin`
- Then: `git remote add origin <your-url>`

### "Please tell me who you are" error
- Run:
  ```bash
  git config --global user.name "Kren Castro"
  git config --global user.email "castrokren@gmail.com"
  ```

### Can't find my GitHub repo after pushing
- Go to https://github.com/your-username
- Look for "Crawler" in your repositories
- Click to view

## After Setup

1. **Share with collaborators**
   - GitHub repo URL: https://github.com/castrokren/Crawler
   - They can clone with: `git clone https://github.com/castrokren/Crawler.git`

2. **Work on improvements**
   - Create branches for each improvement
   - Push regularly
   - Follow the DEVELOPMENT_PLAN.md roadmap

3. **Track issues**
   - Use GitHub Issues to track bugs and improvements
   - Link commits to issues

## Next Steps

1. Install Git (Step 1)
2. Create GitHub repo (Step 3)
3. Run INIT_GIT_REPO.bat (Step 4)
4. Add remote and push (Steps 4-5)
5. Start development and push changes regularly!

---

**Need help?**
- GitHub Help: https://docs.github.com
- Git Guide: https://git-scm.com/book/en/v2
- GitHub CLI: https://cli.github.com
