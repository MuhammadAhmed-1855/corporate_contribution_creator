#!/usr/bin/env python3
"""
Git Contribution README Generator (NDA-Safe, Raw Metadata)
Generates comprehensive README files with year-wise visual heatmaps and package inference.
"""

import subprocess
import re
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import argparse
import sys

import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np


class GitMetricsExtractor:
    def __init__(self, repo_path=".", author_filters=None):
        self.repo_path = repo_path
        self.author_filters = [f.strip().lower() for f in author_filters] if author_filters else []
        self.commits = []
        self.file_stats = []

    def _run_git(self, args):
        try:
            result = subprocess.run(["git"] + args, cwd=self.repo_path, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ Git error: {e.stderr}", file=sys.stderr)
            sys.exit(1)

    def list_all_authors(self):
        print("🔍 Scanning repository for all authors...\n")
        output = self._run_git(["log", "--pretty=format:%an|%ae", "--no-merges"])
        author_counts = Counter()
        for line in output.splitlines():
            if "|" in line:
                name, email = line.split("|", 1)
                author_counts[f"{name} <{email}>"] += 1
        if not author_counts:
            print("⚠️ No commits found.")
            return
        print(f"📊 Found {len(author_counts)} unique author(s):\n")
        print(f"{'Author':<55} {'Commits':<10}")
        print("-" * 65)
        for author, count in author_counts.most_common():
            print(f"{author:<55} {count:<10}")

    def extract_all_data(self):
        print("🔍 Extracting raw commit metadata...")
        self._extract_commits_and_numstat()
        print("🧮 Calculating advanced metrics...")
        return {
            "summary": self._calc_summary(),
            "timeline": self._calc_timeline(),
            "streaks": self._calc_streaks(),
            "time_analysis": self._calc_time_analysis(),
            "packages": self._extract_packages(), 
            "raw_commits": self.commits,
            "date_range": self._calc_date_range()
        }

    def _calc_date_range(self):
        if not self.commits:
            return {"first": None, "last": None, "total_days": 0, "years": []}
        dates = [datetime.strptime(c["date"].split()[0], "%Y-%m-%d") for c in self.commits]
        first_date, last_date = min(dates), max(dates)
        return {
            "first": first_date, "last": last_date,
            "total_days": (last_date - first_date).days + 1,
            "years": list(range(first_date.year, last_date.year + 1))
        }

    def _is_my_commit(self, author_name, author_email):
        if not self.author_filters: return True
        return any(f in author_name.lower() or f in author_email.lower() for f in self.author_filters)

    def _extract_commits_and_numstat(self):
        log_format = "--pretty=format:COMMIT_START|%H|%ai|%an|%ae|%s"
        output = self._run_git(["log", log_format, "--numstat", "--no-merges"])
        current_commit = None

        for line in output.splitlines():
            line = line.strip()
            if not line: continue
            if line.startswith("COMMIT_START|"):
                if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
                    self.commits.append(current_commit)
                parts = line.split("|", 5)
                current_commit = {
                    "hash": parts[1][:8], "date": parts[2], "author": parts[3],
                    "email": parts[4], "message": parts[5], "files": [],
                    "insertions": 0, "deletions": 0
                }
            elif current_commit and "\t" in line:
                parts = line.split("\t")
                if len(parts) == 3:
                    adds = int(parts[0]) if parts[0] != '-' else 0
                    dels = int(parts[1]) if parts[1] != '-' else 0
                    current_commit["insertions"] += adds
                    current_commit["deletions"] += dels
                    current_commit["files"].append({"path": parts[2], "adds": adds, "dels": dels})
                    self.file_stats.append({"path": parts[2], "adds": adds, "dels": dels, "date": current_commit["date"]})
        
        if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
            self.commits.append(current_commit)

    def _calc_summary(self):
        return {
            "total_commits": len(self.commits),
            "total_insertions": sum(c["insertions"] for c in self.commits),
            "total_deletions": sum(c["deletions"] for c in self.commits),
            "net_lines": sum(c["insertions"] for c in self.commits) - sum(c["deletions"] for c in self.commits),
            "total_files_touched": len(set(f["path"] for f in self.file_stats)),
            "authors": dict(Counter(c["author"] for c in self.commits).most_common())
        }

    def _calc_timeline(self):
        return dict(Counter(c["date"].split()[0] for c in self.commits))

    def _calc_streaks(self):
        if not self.commits: return {"current": 0, "longest": 0}
        dates = sorted(set(c["date"].split()[0] for c in self.commits))
        dates_dt = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        longest, current = 1, 1
        for i in range(1, len(dates_dt)):
            if (dates_dt[i] - dates_dt[i-1]).days == 1:
                current += 1; longest = max(longest, current)
            else: current = 1
        if (datetime.now().date() - dates_dt[-1].date()).days > 1: current = 0
        return {"current": current, "longest": longest}

    def _calc_time_analysis(self):
        day_counts, hour_counts = Counter(), Counter()
        for c in self.commits:
            try: dt = datetime.strptime(c["date"], "%Y-%m-%d %H:%M:%S %z")
            except ValueError: dt = datetime.strptime(c["date"], "%Y-%m-%d %H:%M:%S")
            day_counts[dt.strftime("%A")] += 1; hour_counts[dt.hour] += 1
        return {"days_of_week": dict(day_counts), "hours_of_day": dict(hour_counts)}

    def _extract_packages(self):
        """Extract core packages from package.json and requirements.txt."""
        packages = set()
        for root, dirs, files in os.walk(self.repo_path):
            # Ignore hidden folders and dependency folders
            if '.git' in root or 'node_modules' in root or 'venv' in root or '.venv' in root:
                continue
                
            # 1. Parse package.json (JS/TS)
            if 'package.json' in files:
                pkg_path = os.path.join(root, 'package.json')
                try:
                    with open(pkg_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Get dependencies (ignoring devDependencies to reduce noise)
                        deps = data.get('dependencies', {})
                        for pkg in deps.keys():
                            packages.add(pkg)
                except Exception:
                    pass

            # 2. Parse requirements.txt (Python)
            if 'requirements.txt' in files:
                req_path = os.path.join(root, 'requirements.txt')
                try:
                    with open(req_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and not line.startswith('-'):
                                # Handle formats like package==1.0.0 or package>=1.0
                                pkg_name = re.split(r'[=<>!~]', line)[0].strip()
                                if pkg_name:
                                    packages.add(pkg_name)
                except Exception:
                    pass

        # Sort and limit to top 15 to keep the README clean
        return sorted(list(packages))[:15]


class MarkdownRenderer:
    def __init__(self, metrics, repo_name="Project", primary_name=None, output_dir="."):
        self.metrics = metrics
        self.repo_name = repo_name
        self.primary_name = primary_name
        self.output_dir = output_dir

    def render(self):
        md = []
        md.append(self._render_header())
        md.append(self._render_summary_table())
        md.append(self._render_yearly_heatmaps()) # MOVED UP: Graphs are now right below summary
        md.append(self._render_packages())        # MOVED DOWN
        md.append(self._render_time_analysis())
        md.append(self._render_recent_commits())
        md.append(self._render_footer())
        return "\n\n".join(md)

    def generate_full_history(self, main_readme_filename):
        """Generate a separate file with ALL commits, including a back button."""
        commits = self.metrics["raw_commits"]
        if not commits:
            return None
            
        rows = []
        for c in commits:
            date_short = c["date"].split()[0]
            msg = c["message"].replace("|", "\\|")
            rows.append(f"| `{c['hash']}` | {date_short} | {msg} | +{c['insertions']} / -{c['deletions']} |")
        
        table = "\n".join(rows)
        back_button = f"[![← Back to Overview Dashboard](https://img.shields.io/badge/←_Back_to_Overview-Dashboard-007bff?style=for-the-badge)]({main_readme_filename})"
        
        content = (
            f"# 📜 Full Commit History: {self.repo_name}\n\n"
            f"{back_button}\n\n"
            f"*Total Commits: {len(commits)} | Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            "| Hash | Date | Message | LOC Changes |\n"
            "| :--- | :--- | :--- | :--- |\n"
            f"{table}\n\n"
            "---\n*This file contains raw metadata only. No source code is included.*"
        )
        
        filename = "full_commit_history.md"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📜 Generated full history: {path}")
        return filename

    def _render_header(self):
        date_range = self.metrics["date_range"]
        author_info = f" | Author: `{self.primary_name}` (Aggregated aliases)" if self.primary_name else ""
        date_info = ""
        if date_range["first"] and date_range["last"]:
            date_info = f" | Period: {date_range['first'].strftime('%Y-%m-%d')} to {date_range['last'].strftime('%Y-%m-%d')} ({date_range['total_days']} days)"
        
        history_link = "[![View Full Commit History](https://img.shields.io/badge/View-Full_Commit_History-2ea44f?style=for-the-badge)](full_commit_history.md)"
        
        return (
            f"#  {self.repo_name} - Contribution Metrics\n\n"
            f"{history_link}\n\n"
            f"*Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Raw metadata, zero code diffs.{author_info}{date_info}*"
        )

    def _render_summary_table(self):
        s = self.metrics["summary"]
        streaks = self.metrics["streaks"]
        return (
            "## 📈 Summary Statistics\n\n"
            "| Metric | Value | Metric | Value |\n"
            "| :--- | :--- | :--- | :--- |\n"
            f"| **Total Commits** | `{s['total_commits']}` | **Net Lines** | `{s['net_lines']}` |\n"
            f"| **Lines Added** | `+{s['total_insertions']}` | **Files Touched** | `{s['total_files_touched']}` |\n"
            f"| **Lines Removed** | `-{s['total_deletions']}` | **Longest Streak** | `{streaks['longest']} days` 🔥 |\n"
            f"| **Current Streak** | `{streaks['current']} days` | **Unique Aliases** | `{len(s['authors'])}` |"
        )

    def _render_packages(self):
        packages = self.metrics["packages"]
        if not packages:
            return "## 📦 Core Packages & Dependencies\n\n*No package.json or requirements.txt found in this repository.*"
        pkg_list = "\n".join([f"- `{pkg}`" for pkg in packages])
        return (
            "##  Core Packages & Dependencies\n\n"
            "The following key dependencies were utilized in this project:\n\n"
            f"{pkg_list}"
        )

    def _create_single_heatmap(self, timeline, start_date, weeks, year_label):
        days_to_monday = start_date.weekday()
        grid_start = start_date - timedelta(days=days_to_monday)
        data = np.zeros((7, weeks))
        current = grid_start
        for week in range(weeks):
            for day in range(7):
                data[day, week] = timeline.get(current.strftime("%Y-%m-%d"), 0)
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
        ax.set_title(f"Contribution Activity - {year_label}", fontsize=12, color='#c9d1d9', pad=10, fontweight='bold')
        
        image_filename = f"{re.sub(r'[^\w\-_.]', '_', self.repo_name)}_{year_label}.png"
        plt.savefig(os.path.join(self.output_dir, image_filename), dpi=150, bbox_inches='tight', facecolor='#0d1117')
        plt.close()
        return image_filename

    def _render_yearly_heatmaps(self):
        timeline = self.metrics["timeline"]
        date_range = self.metrics["date_range"]
        if not date_range["first"]: return "## 🟩 Contribution Graphs\n\n*No data.*"
        
        images = []
        for year in date_range["years"]:
            images.append(self._create_single_heatmap(timeline, datetime(year, 1, 1), 52, str(year)))
        print(f"🖼️ Generated {len(images)} yearly graphs")
        
        md_parts = ["## 🟩 Contribution Graphs\n"]
        for filename, year in zip(images, date_range["years"]):
            md_parts.append(f"### {year}\n![Contribution Graph {year}]({filename})\n")
        return "\n".join(md_parts)

    def _render_time_analysis(self):
        time_data = self.metrics["time_analysis"]
        if not time_data["days_of_week"]: return "##  Time Analysis\n\n*No data.*"
        peak_day = max(time_data["days_of_week"], key=time_data["days_of_week"].get)
        peak_hour = max(time_data["hours_of_day"], key=time_data["hours_of_day"].get)
        max_h = max(time_data["hours_of_day"].values()) or 1
        chart = "\n".join([f"`{h:02d}:00` {'█' * int((time_data['hours_of_day'].get(h, 0) / max_h) * 20)} ({time_data['hours_of_day'].get(h, 0)})" for h in range(24)])
        return f"## 🕒 Time Analysis\n\n**Peak Productivity:** {peak_day}s at `{peak_hour:02d}:00`\n\n<details>\n<summary><b>24-Hour Distribution</b></summary>\n\n```text\n{chart}\n```\n</details>"

    def _render_recent_commits(self):
        commits = self.metrics["raw_commits"][:20]
        if not commits: return "##  Recent Commits\n\n*None.*"
        rows = [f"| `{c['hash']}` | {c['date'].split()[0]} | {c['message'].replace('|', '\\|')} | +{c['insertions']}/-{c['deletions']} |" for c in commits]
        return f"## 📝 Recent Commits (Top 20)\n\n| Hash | Date | Message | LOC |\n|:---|:---|:---|:---|\n" + "\n".join(rows)

    def _render_footer(self):
        return "---\n*Generated by `github.py`. Raw metadata only. **Zero source code included for NDA compliance.***"


def main():
    parser = argparse.ArgumentParser(description="Generate NDA-safe README.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output-dir", default="D:\\Personal\\corporate_history")
    parser.add_argument("--name", required=True)
    parser.add_argument("--author", default=None)
    parser.add_argument("--primary-name", default=None)
    parser.add_argument("--list-authors", action="store_true")
    parser.add_argument("--output", default="README.md")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    extractor = GitMetricsExtractor(repo_path=args.repo, author_filters=args.author.split(',') if args.author else None)
    if args.list_authors: extractor.list_all_authors(); sys.exit(0)
    
    metrics = extractor.extract_all_data()
    if metrics["summary"]["total_commits"] == 0:
        print("⚠️ No commits found."); sys.exit(0)

    renderer = MarkdownRenderer(metrics, repo_name=args.name, primary_name=args.primary_name, output_dir=args.output_dir)
    
    safe_name = re.sub(r'[^\w\-_.]', '_', args.name)
    main_readme_filename = f"{safe_name}_{args.output}"
    
    # Generate main README
    with open(os.path.join(args.output_dir, main_readme_filename), "w", encoding="utf-8") as f:
        f.write(renderer.render())
    
    # Generate full history file (passing the main readme filename for the back button)
    renderer.generate_full_history(main_readme_filename)

    print(f"✅ Successfully generated files in {args.output_dir}")
    print(f" Stats: {metrics['summary']['total_commits']} commits, +{metrics['summary']['total_insertions']}/-{metrics['summary']['total_deletions']} lines.")

if __name__ == "__main__":
    main()