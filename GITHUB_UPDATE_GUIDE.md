# My Pen V10.0 — GitHub update guide

This package is a **source-code repository update** for My Pen V10.0. It contains the existing Python/PySide6 application, assets, documentation and Windows installer build scripts. No `.exe` is included and **nothing has been pushed to GitHub** by preparing this ZIP.

## বাংলা: Existing GitHub repository আপডেট করবেন যেভাবে

1. `My_Pen_V10.0_GitHub_Ready.zip` **Extract All** করুন।
2. GitHub থেকে আপনার **existing repository** clone করুন অথবা GitHub Desktop-এ খুলুন।
3. Extract করা `My_Pen_V10.0_GitHub_Ready` ফোল্ডারের **ভেতরের সব ফাইল ও ফোল্ডার** (hidden `.github`, `.gitignore`, `.gitattributes` সহ) repository-এর **root folder-এ** কপি করুন। `My_Pen_V10.0_GitHub_Ready` ফোল্ডারটিকে আলাদা nested directory হিসেবে রাখবেন না।
4. আগের repository-এর অন্য কোনো গুরুত্বপূর্ণ ফাইল/কনফিগারেশন overwrite করার আগে changes review করুন। `test-results/`, `.venv/`, `dist/`, `installer-output/` Git-এ commit করবেন না।
5. GitHub Desktop-এ changes review করে **Commit** এবং **Push origin** করুন। অথবা repository root-এ terminal দিয়ে:

   ```bash
   git status
   git add -A
   git commit -m "Update My Pen to V10.0"
   git push
   ```

6. GitHub-এর **Actions** tab-এ `My Pen | Cross-platform tests` workflow-র result দেখুন।
7. Windows installer চাইলে **Actions** → **My Pen | Build Windows installer V10.0** → **Run workflow** দিন। সফল হলে workflow run-এর **Artifacts** থেকে installer এবং portable build পাবেন।

**Important:** ZIP-টিকে GitHub-এ একটি ফাইল হিসেবে upload করলে GitHub এর ভেতরের project files নিজে থেকে extract করবে না। Source update করতে ZIP extract করে contents commit/push করুন। Existing repository-এর history, branches, and settings এই package পরিবর্তন করে না।

## New repository (command-line alternative)

If you are starting with a *new empty* GitHub repository rather than updating an existing one:

```bash
cd My_Pen_V10.0_GitHub_Ready
git init
git add .
git commit -m "Initial My Pen V10.0 source"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

Replace `USERNAME/REPOSITORY` with your own repository. Configure Git identity and authentication if Git prompts for them. If the repository already has commits, use the **existing repository** procedure above instead of running `git init` again.

## What was added for GitHub

- `.gitignore`: excludes local Python environments, caches, build output, generated icons, test reports and local secrets.
- `.gitattributes`: consistent line endings and binary-asset handling.
- `.github/workflows/tests.yml`: Linux + Windows Python 3.12 offscreen tests on push, pull request or manual run.
- `.github/workflows/windows-installer.yml`: builds Windows V10.0 installer and portable output on manual run or `v10.0*` tag.
- `GITHUB_UPDATE_GUIDE.md`: repository-update steps (this file).

## Important scope and privacy notes

- **Original app logic/source/assets are unchanged** in this packaging step. The existing test-result log files are omitted because they are generated artifacts.
- A GitHub Action may fail on a different OS/runner. Review the full error log and address it before treating a build as verified. The Windows installer has **not** been compiled or executed in this package-preparation environment.
- `images/app/developer.png` and social/contact links in `screenpen/developer.py` are present in the source archive. Review them before publishing a **public** repository.
- This package does not create a top-level open-source `LICENSE` for the original code: the copyright/licensing choice belongs to the rights holder. Third-party notices remain in `docs/THIRD_PARTY_NOTICES.md` and bundled icon license files.
- When updating to a newer version later, synchronize version strings in `README.md`, `WINDOWS_BUILD_GUIDE.md`, `installer/MyPen.iss`, `scripts/build_windows.py` and the Windows workflow.

## Run locally

### Windows

Install Python 3.12 x64, then run `setup_windows.bat` and later `run_windows.bat`.

### Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

See [README.md](README.md) for full instructions and [WINDOWS_BUILD_GUIDE.md](WINDOWS_BUILD_GUIDE.md) for native Windows installer creation.
