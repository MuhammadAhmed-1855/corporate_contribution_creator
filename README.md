# 📊 Corporate Contribution Creator (NDA-Safe)

A professional Python tool that generates hierarchical, GitHub-style contribution graphs and comprehensive metric dashboards from your Git history—**without exposing any source code**. 

Perfect for building NDA-compliant **Engineering Impact** case studies for your personal portfolio.

## ✨ Features

- 🏗️ **Hierarchical Drill-Down:** Generates a Master Company Dashboard that links to individual Project Summaries, which in turn link to Full Commit Histories.
- 🔗 **Bi-Directional Navigation:** Automatically generates professional Call-To-Action (CTA) badges to navigate seamlessly between Company, Project, and Commit levels.
- 🟩 **Yearly Contribution Heatmaps:** Generates real PNG images mimicking GitHub's dark-mode contribution graph, split by calendar year.
- 🔒 **NDA-Safe:** Extracts *only* metadata (commit counts, dates, file paths, package names). Zero code diffs or source code are ever read or included.
- 👤 **Author Alias Aggregation:** Combine commits from multiple emails/names (e.g., personal vs. work email) into one unified, accurate profile.
- 📦 **Smart Tech Stack Detection:** Automatically parses `package.json` and `requirements.txt` to list the actual core tech stack used in the project.
- 🔄 **Automated Remote Sync:** Automatically runs `git fetch --all` to ensure UI merges (GitLab/GitHub PRs) are captured, with graceful fallback if offline.
- 📂 **Dynamic Output:** Fully customizable save locations. You are never forced to use a hardcoded directory.


## 🚀 Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/your-username/corporate_contribution_creator.git
   cd corporate_contribution_creator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Requires `matplotlib>=3.8.0` and `numpy>=1.24.0`)*


## 💻 Usage: The Unified Hierarchical Generator

The tool uses a single, powerful script (`hierarchical_generator.py`) on the `main` branch to generate the entire nested ecosystem of files in one run. You no longer need to switch branches or run multiple scripts.

### 📂 Output Files Generated
When you point the script at a company folder, it generates:
1. **`[Company]_Master_README.md`**: The high-level company dashboard with aggregated stats and graphs.
2. **`[Project]_README.md`**: Individual dashboards for each repository found, containing specific stats, tech stacks, and graphs.
3. **`full_commit_history_[Project].md`**: A detailed log of every single commit for each project.
4. **`*.png`**: The visual contribution graph images for both the company and individual projects.

### 🏃‍♂️ How to Run

**Standard Usage:**
```bash
python main.py \
  --parent-dir "/path/to/your/company" \
  --name "Company Name" \
  --author "Name 1, Name 2" \
  --primary-name "Muhammad Ahmed" \
  --back-to "https://github.com/your-username"
```
*(Note: On Windows, you can use `py` instead of `python`)*

**Advanced Usage (Custom Output & Offline Mode):**
```bash
python main.py \
  --parent-dir "/path/to/your/company" \
  --name "Company Name" \
  --author "Your Name, your.email@domain.com" \
  --primary-name "Your Display Name" \
  --output-dir "/path/to/your/output" \
  --skip-fetch
```

### ⚙️ Command Line Arguments

| Argument | Required? | Description |
| :--- | :---: | :--- |
| `--parent-dir` | ✅ Yes* | The top-level folder to recursively scan for Git repositories (Used in Hierarchical mode). |
| `--repo` | ✅ Yes* | The exact path to a single Git repository (Used in legacy Single-Project mode). |
| `--name` | ✅ Yes | The Company or Project name (used in the header and output filenames). |
| `--author` | ✅ Yes | Comma-separated list of your Git names/emails to filter and aggregate your commits. |
| `--primary-name` | ✅ Yes | Your clean, professional display name for the README headers. |
| `--output-dir` | ❌ No | **Dynamic!** Where to save the generated files. Defaults to `D:\Personal\corporate_history`, but can be set to any folder (e.g., `--output-dir "C:\MyPortfolio"`). |
| `--back-to` | ❌ No | **Highly Recommended.** The URL to link back to from the Company Master README (e.g., your main GitHub profile or personal portfolio site). |
| `--skip-fetch` | ❌ No | Skips the automatic `git fetch --all` (useful if intentionally working offline or on a slow connection). |
| `--list-authors` | ❌ No | *(Single-Project mode only)* Scans the repo and prints all unique authors with commit counts. Great for finding your exact Git aliases if your count looks too low. |

*\*Note: Use `--parent-dir` for the unified hierarchical generator, or `--repo` if you are running the standalone single-project script.*


## 🗺️ The Navigation Flow

The generated files create a seamless, bi-directional navigation experience for anyone reviewing your portfolio:

1. **Master Dashboard** (`[Company]_Master_README.md`): 
   - Shows company-wide aggregated stats and graphs. 
   - Contains a `👤 Back to Main Portfolio` button (if `--back-to` is used). 
   - Contains a table of projects with `📄 View Summary` links.
2. **Project Summary** (`[Project]_README.md`): 
   - Shows specific stats, tech stack, and graphs for one repo. 
   - Contains `🏢 Back to Company Overview` and `📜 View Full Commit Log` buttons.
3. **Full History** (`full_commit_history_[Project].md`): 
   - A detailed, scrollable log of every single commit. 
   - Contains an `⬅️ Back to Project Summary` button to return to the dashboard.


## 🧠 How the Aggregator Works Under the Hood

1. It recursively walks through the `--parent-dir` looking for `.git` folders.
2. It automatically runs `git fetch --all` to ensure remote UI merges (like GitLab/GitHub PRs) are captured locally.
3. It extracts **only your commits** from each repository based on the `--author` filter (scanning all branches with `--all`).
4. It merges the daily commit counts to create a single, accurate "Company-Wide" contribution graph per year.
5. It generates a clean table breaking down your contribution per project, including a concise "Primary Tech Stack" summary for each specific project (avoiding messy, global dependency lists).


## 💡 Pro-Tips for Best Results

1. **Finding your aliases:** If your commit count looks too low, you can temporarily run `python hierarchical_generator.py --parent-dir "path" --name "Test" --author "Test" --primary-name "Test" --list-authors` (if using the legacy single-repo mode) or simply check `git log --pretty=format:"%an <%ae>" | sort | uniq -c | sort -nr` to see exactly how your name was spelled in the Git history. Copy-paste those exact strings into the `--author` flag.
2. **Dynamic Output:** You don't have to use the default output folder. Pass `--output-dir "C:\Users\Shiroe\Desktop\Portfolio"` to save the generated files anywhere you want!
3. **Monorepos:** If a single repository contains multiple distinct projects, point `--parent-dir` to the specific subdirectory containing the `.git` folder to generate a dedicated impact report for that monorepo.


## 🛡️ NDA Compliance Guarantee

This tool strictly uses `git log --numstat` and basic file system parsing for config files (`package.json`, `requirements.txt`). It **never** runs `git show`, `git diff`, or reads the actual contents of your source code files. The generated output is 100% safe to share publicly on GitHub, LinkedIn, or in job applications.

---

*Built with ❤️ for engineers who want to showcase their impact without compromising confidentiality.*