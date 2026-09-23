# 📊 Corporate Contribution Creator (NDA-Safe)

A professional Python tool that generates beautiful, GitHub-style contribution graphs and comprehensive metric dashboards from your Git history—**without exposing any source code**. Perfect for building NDA-compliant engineering portfolios.

## ✨ Features
- 🟩 **Yearly Contribution Heatmaps:** Generates real PNG images mimicking GitHub's dark-mode contribution graph, split by calendar year.
- 🔒 **NDA-Safe:** Extracts *only* metadata (commit counts, dates, file paths, package names). Zero code diffs are included.
- 👤 **Author Alias Aggregation:** Combine commits from multiple emails/names (e.g., personal vs. work email) into one unified profile.
- 📦 **Smart Package Detection:** Automatically parses `package.json` and `requirements.txt` to list the actual tech stack used.
- 🔗 **Dual-View Navigation:** Generates a main dashboard README and a separate, linked `full_commit_history.md` file.

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/corporate_contribution_creator.git
   cd corporate_contribution_creator