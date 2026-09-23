# 📊 Corporate Contribution Creator (NDA-Safe)

A professional Python tool that generates beautiful, GitHub-style contribution graphs and comprehensive metric dashboards from your Git history—**without exposing any source code**. Perfect for building NDA-compliant engineering portfolios.

## ✨ Features

- 🟩 **Yearly Contribution Heatmaps:** Generates real PNG images mimicking GitHub's dark-mode contribution graph, split by calendar year.
- 🔒 **NDA-Safe:** Extracts *only* metadata (commit counts, dates, file paths, package names). Zero code diffs or source code are ever read or included.
- 👤 **Author Alias Aggregation:** Combine commits from multiple emails/names (e.g., personal vs. work email) into one unified, accurate profile.
- 📦 **Smart Package Detection:** Automatically parses `package.json` and `requirements.txt` to list the actual core tech stack used in the project.
- 🔗 **Dual-View Navigation:** Generates a main dashboard `README.md` and a separate, linked `full_commit_history.md` file for deep dives.
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
   *(Requires `matplotlib` and `numpy`)*

3. **Choose your branch:**
   - For a **single project**, stay on the `main` branch (or `feature/repositoryContributor`).
   - For a **company-wide portfolio**, switch to the `feature/companyContributor` branch:
     ```bash
     git checkout feature/companyContributor
     ```


## 💻 Usage Guide 1: Single Project Analyzer (`main` branch)

Use this to generate a deep-dive contribution dashboard for **one specific Git repository**.

###  Output Files Generated
1. `[ProjectName]_README.md`: The main dashboard with stats, graphs, and packages.
2. `full_commit_history.md`: A detailed log of every single commit (linked via a button in the main README).
3. `[ProjectName]_2024.png`, `[ProjectName]_2025.png`, etc.: The visual contribution graph images.

### 🏃‍♂️ How to Run

**Basic Usage:**
```bash
python main.py --repo "/path/to/your/project" --name "My Project Name" --author "Your Name" --primary-name "Your Display Name"
```
*(Note: On Windows, you can use `py` instead of `python`)*

**Advanced Usage (Multiple Aliases & Custom Output):**
```bash
python main.py \
  --repo "/path/to/your/project" \
  --name "My Project Name" \
  --author "Name 1, Name 2" \
  --primary-name "Your Display Name" \
  --output-dir "/path/to/your/output"
```

### ⚙️ Command Line Arguments

| Argument | Required? | Description |
| :--- | :---: | :--- |
| `--repo` | ✅ Yes | The exact path to the Git repository you want to analyze. |
| `--name` | ✅ Yes | The display name for the project (used in the header and filenames). |
| `--author` | ❌ No | Comma-separated list of your Git names/emails. If omitted, it counts *everyone*. |
| `--primary-name` | ❌ No | The clean name to display in the README header (e.g., "Muhammad Ahmed"). |
| `--output-dir` | ❌ No | **Dynamic!** Where to save the files. Defaults to `D:\Personal\corporate_history`, but can be set to any folder (e.g., `--output-dir "C:\MyPortfolio"`). |
| `--list-authors` | ❌ No | Scans the repo and prints all unique authors. Great for finding your exact Git aliases if your commit count looks too low. |

## 💻 Usage Guide 2: Company-Wide Aggregator (`feature/companyContributor` branch)

Use this to recursively scan a parent folder containing **multiple Git repositories**, aggregate your personal stats across all of them, and generate one master "Company Portfolio" dashboard.

###  Output Files Generated
1. `[CompanyName]_Master_README.md`: The high-level company dashboard.
2. `[CompanyName]_Aggregated_2024.png`, etc.: Combined contribution graphs summing up your work across all projects for that specific year.

### ‍♂️ How to Run

**Basic Usage:**
```bash
python portfolio_aggregator.py --parent-dir "/path/to/company-folder" --name "Company Name" --author "Your Name" --primary-name "Your Display Name"
```

**Advanced Usage (Custom Output Directory):**
```bash
python portfolio_aggregator.py \
  --parent-dir "/path/to/company-folder" \
  --name "Company Name" \
  --author "Name 1, Name 2" \
  --primary-name "Your Display Name" \
  --output-dir "/path/to/your/output"
```

### ⚙️ Command Line Arguments

| Argument | Required? | Description |
| :--- | :---: | :--- |
| `--parent-dir` | ✅ Yes | The top-level folder to recursively scan for Git repositories. |
| `--name` | ✅ Yes | The Company or Portfolio name (used in the header and filenames). |
| `--author` | ✅ Yes | Comma-separated list of your Git names/emails to filter and aggregate your commits. |
| `--primary-name` | ✅ Yes | The clean name to display in the README header. |
| `--output-dir` | ❌ No | **Dynamic!** Where to save the files. Defaults to `/path/to/your/output`, but can be set to any folder. |

### 🧠 How the Aggregator Works
1. It recursively walks through the `--parent-dir` looking for `.git` folders.
2. It extracts **only your commits** from each repository based on the `--author` filter.
3. It merges the daily commit counts to create a single, accurate "Company-Wide" contribution graph per year.
4. It generates a clean table breaking down your contribution per project, including a concise "Primary Tech Stack" summary for each specific project (avoiding messy, global dependency lists).


## 💡 Pro-Tips for Best Results

1. **Finding your aliases:** If your commit count looks too low, run `python main.py --repo "path" --list-authors` to see exactly how your name was spelled in the Git history, then copy-paste those exact strings into the `--author` flag.
2. **Dynamic Output:** You don't have to use the default output folder. Pass `--output-dir "/path/to/your/output"` to save the generated files anywhere you want!
3. **Monorepos:** If a single repository contains multiple distinct projects, use the **Single Project Analyzer** but point it to the specific subdirectory (e.g., `--repo "/path/to/your/project"`).


## ️ NDA Compliance Guarantee

This tool strictly uses `git log --numstat` and basic file system parsing for config files. It **never** runs `git show`, `git diff`, or reads the actual contents of your source code files. The generated output is 100% safe to share publicly on GitHub or in job applications.

---

*Built with ❤️ for engineers who want to showcase their impact without compromising confidentiality.*