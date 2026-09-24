#!/usr/bin/env python3
"""
Portfolio Aggregator: Generates a master README for a company/folder containing multiple Git repos.
Searches recursively for all .git folders.
"""

import subprocess
import re
import os
import json
from datetime import datetime, timedelta
from collections import Counter
import argparse
import sys

import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np


class GitMetricsExtractor:
    def __init__(self, repo_path=".", author_filters=None, fetch_remote=True):
        self.repo_path = repo_path
        self.author_filters = [f.strip().lower() for f in author_filters] if author_filters else []
        self.fetch_remote = fetch_remote
        self.commits = []
        self.file_stats = []

    def _run_git(self, args):
        try:
            result = subprocess.run(["git"] + args, cwd=self.repo_path, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return "" 

    def _fetch_latest(self):
        """Automatically fetch latest remote data, but fail gracefully if offline."""
        if not self.fetch_remote:
            return
        print("  🔄 Fetching latest remote data...")
        try:
            subprocess.run(["git", "fetch", "--all", "--quiet"], cwd=self.repo_path, capture_output=True, text=True, check=False)
        except Exception:
            pass

    def _is_my_commit(self, author_name, author_email):
        if not self.author_filters: return True
        return any(f in author_name.lower() or f in author_email.lower() for f in self.author_filters)

    def extract_data(self):
        self._fetch_latest()
        log_format = "--pretty=format:COMMIT_START|%H|%ai|%an|%ae|%s"
        output = self._run_git(["log", log_format, "--numstat", "--no-merges", "--all"])
        if not output: return None

        current_commit = None
        for line in output.splitlines():
            line = line.strip()
            if not line: continue
            if line.startswith("COMMIT_START|"):
                if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
                    self.commits.append(current_commit)
                parts = line.split("|", 5)
                current_commit = {"hash": parts[1][:8], "date": parts[2], "author": parts[3], "email": parts[4], "message": parts[5], "insertions": 0, "deletions": 0}
            elif current_commit and "\t" in line:
                parts = line.split("\t")
                if len(parts) == 3:
                    adds = int(parts[0]) if parts[0] != '-' else 0
                    dels = int(parts[1]) if parts[1] != '-' else 0
                    current_commit["insertions"] += adds
                    current_commit["deletions"] += dels
                    self.file_stats.append({"path": parts[2]})
        if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
            self.commits.append(current_commit)

        if not self.commits: return None

        dates = [datetime.strptime(c["date"].split()[0], "%Y-%m-%d") for c in self.commits]
        return {
            "total_commits": len(self.commits),
            "total_insertions": sum(c["insertions"] for c in self.commits),
            "total_deletions": sum(c["deletions"] for c in self.commits),
            "net_lines": sum(c["insertions"] for c in self.commits) - sum(c["deletions"] for c in self.commits),
            "merges": self._calc_merges(),
            "first_date": min(dates),
            "last_date": max(dates),
            "timeline": Counter(c["date"].split()[0] for c in self.commits),
            "primary_tech": self._get_primary_tech()
        }

    def _calc_merges(self):
        output = self._run_git(["log", "--merges", "--pretty=format:COMMIT_START|%an|%ae", "--all"])
        merge_count = 0
        for line in output.splitlines():
            if line.startswith("COMMIT_START|"):
                parts = line.split("|")
                if len(parts) >= 3 and self._is_my_commit(parts[1], parts[2]):
                    merge_count += 1
        return merge_count

    def _get_primary_tech(self):
        tech_indicators = []
        for root, dirs, files in os.walk(self.repo_path):
            if '.git' in root or 'node_modules' in root or 'venv' in root: continue
            if 'package.json' in files:
                try:
                    with open(os.path.join(root, 'package.json'), 'r', encoding='utf-8') as f:
                        deps = json.load(f).get('dependencies', {})
                        major_frameworks = [p for p in deps.keys() if any(fw in p.lower() for fw in ['react', 'next', 'vue', 'angular', 'express', 'nestjs', 'tailwind', 'prisma', 'typeorm', 'axios'])]
                        tech_indicators.extend(major_frameworks[:2])
                except Exception: pass
            if 'requirements.txt' in files:
                try:
                    with open(os.path.join(root, 'requirements.txt'), 'r', encoding='utf-8') as f:
                        for line in f:
                            pkg = re.split(r'[=<>!~]', line.strip())[0].strip()
                            if pkg and any(fw in pkg.lower() for fw in ['django', 'flask', 'fastapi', 'pandas', 'numpy', 'sqlalchemy', 'celery']):
                                tech_indicators.append(pkg)
                except Exception: pass
            if any(f.endswith('.csproj') or f.endswith('.sln') for f in files): tech_indicators.append('.NET')
            if any(f == 'go.mod' for f in files): tech_indicators.append('Go')
        unique_tech = list(dict.fromkeys(tech_indicators))[:3]
        return ", ".join(unique_tech) if unique_tech else "Standard Stack"


def create_aggregated_heatmap(all_timelines, start_date, weeks, output_dir, filename):
    days_to_monday = start_date.weekday()
    grid_start = start_date - timedelta(days=days_to_monday)
    data = np.zeros((7, weeks))
    current = grid_start
    for week in range(weeks):
        for day in range(7):
            date_str = current.strftime("%Y-%m-%d")
            total_commits = sum(timeline.get(date_str, 0) for timeline in all_timelines)
            data[day, week] = total_commits
            current += timedelta(days=1)

    fig, ax = plt.subplots(figsize=(15, 3))
    colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    cmap = mcolors.ListedColormap(colors)
    norm = mcolors.BoundaryNorm([0, 1, 2, 3, 4, 5], cmap.N)
    ax.pcolormesh(data, cmap=cmap, norm=norm, edgecolors='#0d1117', linewidth=0.5)
    ax.set_yticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5])
    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], fontsize=8, color='#8b949e')
    ax.set_xticks([])
    ax.set_facecolor('#0d1117')
    fig.patch.set_facecolor('#0d1117')
    for spine in ax.spines.values(): spine.set_visible(False)
    end_date = grid_start + timedelta(weeks=weeks) - timedelta(days=1)
    ax.set_title(f"Company-Wide Contribution Activity ({start_date.strftime('%Y')} - {end_date.strftime('%Y')})", fontsize=12, color='#c9d1d9', pad=10, fontweight='bold')
    plt.savefig(os.path.join(output_dir, filename), dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    return filename


def main():
    parser = argparse.ArgumentParser(description="Aggregate multiple Git repos into one portfolio README.")
    parser.add_argument("--parent-dir", required=True, help="Top-level folder to scan for Git repositories")
    parser.add_argument("--output-dir", default="D:\\Personal\\corporate_history")
    parser.add_argument("--name", required=True, help="Company or Portfolio Name")
    parser.add_argument("--author", required=True, help="Comma-separated list of your author names/emails")
    parser.add_argument("--primary-name", required=True, help="Your clean display name")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip git fetch --all (useful if offline)")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    author_filters = [f.strip() for f in args.author.split(',')]
    projects = []
    global_first_date, global_last_date = None, None

    print(f"🔍 Recursively scanning {args.parent_dir} for Git repositories...")
    for root, dirs, files in os.walk(args.parent_dir):
        if '.git' in dirs:
            repo_path = root
            dirs.remove('.git') 
            project_name = os.path.basename(repo_path)
            if project_name.lower() in ['src', 'app', 'web', 'api', 'backend', 'frontend']:
                project_name = os.path.relpath(repo_path, args.parent_dir).replace('\\', '/')
            print(f"  Found repo: {project_name}")
            
            extractor = GitMetricsExtractor(
                repo_path=repo_path, 
                author_filters=author_filters,
                fetch_remote=not args.skip_fetch
            )
            metrics = extractor.extract_data()
            if metrics:
                projects.append({"name": project_name, "metrics": metrics})
                if global_first_date is None or metrics["first_date"] < global_first_date: global_first_date = metrics["first_date"]
                if global_last_date is None or metrics["last_date"] > global_last_date: global_last_date = metrics["last_date"]

    if not projects:
        print("⚠️ No valid Git repositories with matching commits found.")
        sys.exit(0)

    total_commits = sum(p["metrics"]["total_commits"] for p in projects)
    total_insertions = sum(p["metrics"]["total_insertions"] for p in projects)
    total_deletions = sum(p["metrics"]["total_deletions"] for p in projects)
    total_merges = sum(p["metrics"]["merges"] for p in projects)

    print(f"🖼️ Generating aggregated company-wide heatmap...")
    years = list(range(global_first_date.year, global_last_date.year + 1))
    heatmap_files = []
    for year in years:
        filename = f"{re.sub(r'[^\w\-_.]', '_', args.name)}_Aggregated_{year}.png"
        create_aggregated_heatmap([p["metrics"]["timeline"] for p in projects], datetime(year, 1, 1), 52, args.output_dir, filename)
        heatmap_files.append((filename, year))

    safe_name = re.sub(r'[^\w\-_.]', '_', args.name)
    readme_path = os.path.join(args.output_dir, f"{safe_name}_Master_README.md")
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# 🏢 {args.name} - Engineering Portfolio\n\n")
        f.write(f"*Author: `{args.primary_name}` | Period: {global_first_date.strftime('%Y-%m-%d')} to {global_last_date.strftime('%Y-%m-%d')}*\n\n")
        f.write("## 📈 Aggregate Summary Statistics\n\n")
        f.write("| Metric | Value |\n| :--- | :--- |\n")
        f.write(f"| **Total Projects** | `{len(projects)}` |\n")
        f.write(f"| **Total Commits** | `{total_commits}` |\n")
        f.write(f"| **Merges / Reviews** | `{total_merges}` 🤝 |\n")
        f.write(f"| **Net Lines of Code** | `+{total_insertions - total_deletions}` |\n\n")
        f.write("##  Company-Wide Contribution Graphs\n\n")
        for filename, year in heatmap_files:
            f.write(f"### {year}\n![Contribution Graph {year}]({filename})\n\n")
        f.write("## 📂 Project Breakdown\n\n")
        f.write("| Project | Primary Tech Stack | Commits | Merges | Lines Added | Lines Removed |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for p in projects:
            m = p["metrics"]
            tech = m["primary_tech"]
            f.write(f"| **{p['name']}** | `{tech}` | {m['total_commits']} | {m['merges']} | +{m['total_insertions']} | -{m['total_deletions']} |\n")
        f.write("\n---\n*Generated by Corporate Contribution Calculator. Raw metadata only. Zero source code included.*")

    print(f"✅ Successfully generated Master Portfolio: {readme_path}")

if __name__ == "__main__":
    main()