#!/usr/bin/env python3
"""
Git Contribution README Generator (NDA-Safe, Raw Metadata)
Generates comprehensive README files with year-wise visual heatmaps.
"""

import subprocess
import re
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import argparse
import sys

# Import matplotlib for the heatmap
import matplotlib
matplotlib.use('Agg') # Prevent GUI popups on Windows
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np


class GitMetricsExtractor:
    """Phase 1: Extract and calculate all raw metrics from Git."""

    def __init__(self, repo_path=".", author_filters=None):
        self.repo_path = repo_path
        self.author_filters = [f.strip().lower() for f in author_filters] if author_filters else []
        self.commits = []
        self.file_stats = []

    def _run_git(self, args):
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ Git error: {e.stderr}", file=sys.stderr)
            sys.exit(1)

    def list_all_authors(self):
        print("🔍 Scanning repository for all authors...\n")
        log_format = "--pretty=format:%an|%ae"
        output = self._run_git(["log", log_format, "--no-merges"])
        
        author_counts = Counter()
        for line in output.splitlines():
            if "|" in line:
                name, email = line.split("|", 1)
                author_counts[f"{name} <{email}>"] += 1
        
        if not author_counts:
            print("⚠️ No commits found in this repository.")
            return
        
        print(f" Found {len(author_counts)} unique author(s):\n")
        print(f"{'Author':<55} {'Commits':<10}")
        print("-" * 65)
        for author, count in author_counts.most_common():
            print(f"{author:<55} {count:<10}")
        print(f"\n💡 Tip: Use --author with a comma-separated list of your aliases.")

    def extract_all_data(self):
        print("🔍 Extracting raw commit metadata...")
        self._extract_commits_and_numstat()

        print("🧮 Calculating advanced metrics...")
        return {
            "summary": self._calc_summary(),
            "timeline": self._calc_timeline(),
            "streaks": self._calc_streaks(),
            "time_analysis": self._calc_time_analysis(),
            "languages": self._calc_languages(),
            "top_files": self._calc_top_files(),
            "raw_commits": self.commits,
            "date_range": self._calc_date_range()
        }

    def _calc_date_range(self):
        """Calculate the overall date range of commits."""
        if not self.commits:
            return {"first": None, "last": None, "total_days": 0, "years": []}
        
        dates = [datetime.strptime(c["date"].split()[0], "%Y-%m-%d") for c in self.commits]
        first_date = min(dates)
        last_date = max(dates)
        total_days = (last_date - first_date).days + 1
        
        # Extract all unique years involved
        years = list(range(first_date.year, last_date.year + 1))
        
        return {
            "first": first_date,
            "last": last_date,
            "total_days": total_days,
            "years": years
        }

    def _is_my_commit(self, author_name, author_email):
        if not self.author_filters:
            return True
        name_lower = author_name.lower()
        email_lower = author_email.lower()
        return any(f in name_lower or f in email_lower for f in self.author_filters)

    def _extract_commits_and_numstat(self):
        log_format = "--pretty=format:COMMIT_START|%H|%ai|%an|%ae|%s"
        output = self._run_git(["log", log_format, "--numstat", "--no-merges"])

        current_commit = None

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("COMMIT_START|"):
                if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
                    self.commits.append(current_commit)

                parts = line.split("|", 5)
                current_commit = {
                    "hash": parts[1][:8],
                    "date": parts[2],
                    "author": parts[3],
                    "email": parts[4],
                    "message": parts[5],
                    "files": [],
                    "insertions": 0,
                    "deletions": 0
                }
            elif current_commit and "\t" in line:
                parts = line.split("\t")
                if len(parts) == 3:
                    adds, dels, filepath = parts
                    adds = int(adds) if adds != '-' else 0
                    dels = int(dels) if dels != '-' else 0

                    current_commit["insertions"] += adds
                    current_commit["deletions"] += dels
                    current_commit["files"].append({"path": filepath, "adds": adds, "dels": dels})
                    self.file_stats.append({"path": filepath, "adds": adds, "dels": dels, "date": current_commit["date"]})

        if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
            self.commits.append(current_commit)

    def _calc_summary(self):
        total_commits = len(self.commits)
        total_adds = sum(c["insertions"] for c in self.commits)
        total_dels = sum(c["deletions"] for c in self.commits)
        total_files_touched = len(set(f["path"] for f in self.file_stats))
        authors = Counter(c["author"] for c in self.commits)

        return {
            "total_commits": total_commits,
            "total_insertions": total_adds,
            "total_deletions": total_dels,
            "net_lines": total_adds - total_dels,
            "total_files_touched": total_files_touched,
            "authors": dict(authors.most_common())
        }

    def _calc_timeline(self):
        daily_counts = Counter()
        for c in self.commits:
            date_str = c["date"].split()[0]
            daily_counts[date_str] += 1
        return dict(daily_counts)

    def _calc_streaks(self):
        if not self.commits:
            return {"current": 0, "longest": 0}
        dates = sorted(list(set(c["date"].split()[0] for c in self.commits)))
        dates_dt = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        longest = 1
        current = 1
        for i in range(1, len(dates_dt)):
            if (dates_dt[i] - dates_dt[i-1]).days == 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        today = datetime.now().date()
        last_commit_date = dates_dt[-1].date()
        if (today - last_commit_date).days > 1:
            current = 0
        return {"current": current, "longest": longest}

    def _calc_time_analysis(self):
        day_counts = Counter()
        hour_counts = Counter()
        for c in self.commits:
            date_str = c["date"]
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
            except ValueError:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            day_counts[dt.strftime("%A")] += 1
            hour_counts[dt.hour] += 1
        return {"days_of_week": dict(day_counts), "hours_of_day": dict(hour_counts)}

    def _calc_languages(self):
        ext_counts = Counter()
        for f in self.file_stats:
            ext = os.path.splitext(f["path"])[1].lower()
            if ext: ext_counts[ext] += 1
        return dict(ext_counts.most_common(10))

    def _calc_top_files(self):
        file_commit_counts = Counter(f["path"] for f in self.file_stats)
        return dict(file_commit_counts.most_common(10))


class MarkdownRenderer:
    """Phase 2: Render the extracted metrics into a beautiful README.md."""

    def __init__(self, metrics, repo_name="Project", primary_name=None, output_dir="."):
        self.metrics = metrics
        self.repo_name = repo_name
        self.primary_name = primary_name
        self.output_dir = output_dir

    def render(self):
        md = []
        md.append(self._render_header())
        md.append(self._render_summary_table())
        md.append(self._render_yearly_heatmaps()) # Year-wise graphs
        md.append(self._render_time_analysis())
        md.append(self._render_languages_and_files())
        md.append(self._render_recent_commits())
        md.append(self._render_footer())
        return "\n\n".join(md)

    def _render_header(self):
        date_range = self.metrics["date_range"]
        author_info = f" | Author: `{self.primary_name}` (Aggregated aliases)" if self.primary_name else ""
        
        date_info = ""
        if date_range["first"] and date_range["last"]:
            first_str = date_range["first"].strftime("%Y-%m-%d")
            last_str = date_range["last"].strftime("%Y-%m-%d")
            total_days = date_range["total_days"]
            date_info = f" | Period: {first_str} to {last_str} ({total_days} days)"
        
        return (
            f"#  {self.repo_name} - Contribution Metrics\n\n"
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
            f"| **Current Streak** | `{streaks['current']} days` | **Unique Aliases Used** | `{len(s['authors'])}` |"
        )

    def _create_single_heatmap(self, timeline, start_date, weeks, year_label):
        """Create a single 52-week heatmap graph for a specific year."""
        # Align start date to Monday (like GitHub)
        days_to_monday = start_date.weekday()
        grid_start = start_date - timedelta(days=days_to_monday)
        
        # Build data matrix (7 rows x weeks columns)
        data = np.zeros((7, weeks))
        
        current = grid_start
        for week in range(weeks):
            for day in range(7):
                date_str = current.strftime("%Y-%m-%d")
                data[day, week] = timeline.get(date_str, 0)
                current += timedelta(days=1)

        # Generate the plot
        fig, ax = plt.subplots(figsize=(15, 3))
        
        # GitHub-like green colormap
        colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
        cmap = mcolors.ListedColormap(colors)
        
        # Custom normalization: 0, 1, 2, 3, 4+
        bounds = [0, 1, 2, 3, 4, 5]
        norm = mcolors.BoundaryNorm(bounds, cmap.N)
        
        ax.pcolormesh(data, cmap=cmap, norm=norm, edgecolors='#0d1117', linewidth=0.5)
        
        ax.set_yticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5])
        ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], fontsize=8, color='#8b949e')
        ax.set_xticks([])
        
        # Style the plot
        ax.set_facecolor('#0d1117')
        fig.patch.set_facecolor('#0d1117')
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Add title with the year
        ax.set_title(f"Contribution Activity - {year_label}", fontsize=12, color='#c9d1d9', pad=10, fontweight='bold')
        
        # Save the image
        image_filename = f"{re.sub(r'[^\w\-_.]', '_', self.repo_name)}_{year_label}.png"
        image_path = os.path.join(self.output_dir, image_filename)
        plt.savefig(image_path, dpi=150, bbox_inches='tight', facecolor='#0d1117')
        plt.close()
        
        return image_filename

    def _render_yearly_heatmaps(self):
        """Generate year-wise 52-week contribution graphs."""
        timeline = self.metrics["timeline"]
        date_range = self.metrics["date_range"]
        
        if not date_range["first"] or not date_range["last"]:
            return "## 🟩 Contribution Graphs\n\n*No commit data available.*"
        
        years = date_range["years"]
        image_filenames = []
        
        # Create a graph for each year
        for year in years:
            start_date = datetime(year, 1, 1)
            weeks = 52 # Exactly 52 weeks per graph as requested
            
            # Create the graph
            image_filename = self._create_single_heatmap(
                timeline, 
                start_date, 
                weeks, 
                str(year)
            )
            image_filenames.append((image_filename, year))
        
        print(f"️ Generated {len(image_filenames)} yearly contribution graph(s)")
        
        # Build markdown output
        md_parts = ["## 🟩 Contribution Graphs\n"]
        
        for filename, year in image_filenames:
            md_parts.append(f"### {year}\n")
            md_parts.append(f"![Contribution Graph {year}]({filename})\n")
        
        return "\n".join(md_parts)

    def _render_time_analysis(self):
        time_data = self.metrics["time_analysis"]
        if not time_data["days_of_week"] or not time_data["hours_of_day"]:
            return "## 🕒 Time Analysis\n\n*No commit data available for time analysis.*"

        peak_day = max(time_data["days_of_week"], key=time_data["days_of_week"].get)
        peak_hour = max(time_data["hours_of_day"], key=time_data["hours_of_day"].get)

        max_hour_count = max(time_data["hours_of_day"].values()) if time_data["hours_of_day"] else 1
        hour_chart = []
        for h in range(24):
            count = time_data["hours_of_day"].get(h, 0)
            bar_len = int((count / max_hour_count) * 20)
            bar = "█" * bar_len
            hour_chart.append(f"`{h:02d}:00` {bar} ({count})")

        chart_text = "\n".join(hour_chart)
        return (
            "##  Time Analysis\n\n"
            f"**Peak Productivity:** {peak_day}s at `{peak_hour:02d}:00`\n\n"
            "<details>\n"
            "<summary><b>Click to expand 24-Hour Commit Distribution</b></summary>\n\n"
            "```text\n"
            f"{chart_text}\n"
            "```\n"
            "</details>"
        )

    def _render_languages_and_files(self):
        langs = self.metrics["languages"]
        top_files = self.metrics["top_files"]
        lang_rows = "\n".join([f"| `{ext}` | {count} |" for ext, count in langs.items()]) if langs else "| *No files detected* | - |"
        file_rows = "\n".join([f"| `{path}` | {count} |" for path, count in top_files.items()]) if top_files else "| *No files detected* | - |"
        return (
            "## 🛠️ Languages & Hotspots\n\n"
            "### Inferred Languages (by file extension)\n"
            "| Extension | Files Touched |\n"
            "| :--- | :--- |\n"
            f"{lang_rows}\n\n"
            "### Most Frequently Modified Files (Hotspots)\n"
            "| File Path | Times Modified |\n"
            "| :--- | :--- |\n"
            f"{file_rows}"
        )

    def _render_recent_commits(self):
        commits = self.metrics["raw_commits"][:20]
        if not commits:
            return "## 📝 Recent Commits\n\n*No commits found.*"
        rows = []
        for c in commits:
            date_short = c["date"].split()[0]
            msg = c["message"].replace("|", "\\|")
            rows.append(f"| `{c['hash']}` | {date_short} | {msg} | +{c['insertions']} / -{c['deletions']} |")
        return (
            "## 📝 Recent Commits (Raw Metadata)\n\n"
            "| Hash | Date | Message (Unsanitized) | LOC Changes |\n"
            "| :--- | :--- | :--- | :--- |\n"
            f"{'\n'.join(rows)}"
        )

    def _render_footer(self):
        return (
            "---\n"
            "*Generated by `github.py`. This document contains raw metadata and statistics. "
            "**Zero source code or diffs are included to ensure strict NDA compliance.***"
        )


def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive NDA-safe README files.")
    parser.add_argument("--repo", required=True, help="Path to the git repository")
    parser.add_argument("--output-dir", default="D:\\Personal\\corporate_history", help="Directory to save files")
    parser.add_argument("--name", default=None, help="Project name")
    parser.add_argument("--author", default=None, help="Comma-separated list of author names/emails")
    parser.add_argument("--primary-name", default=None, help="Clean name for the header")
    parser.add_argument("--list-authors", action="store_true", help="List all authors and exit")
    parser.add_argument("--output", default="README.md", help="Output filename")

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    author_filters = [a.strip() for a in args.author.split(',')] if args.author else None
    extractor = GitMetricsExtractor(repo_path=args.repo, author_filters=author_filters)
    
    if args.list_authors:
        extractor.list_all_authors()
        sys.exit(0)
    
    if not args.name:
        print("❌ Error: --name is required")
        sys.exit(1)
    
    metrics = extractor.extract_all_data()

    if metrics["summary"]["total_commits"] == 0:
        print("⚠️ No commits found matching your author filters.")
        sys.exit(0)

    renderer = MarkdownRenderer(metrics, repo_name=args.name, primary_name=args.primary_name, output_dir=args.output_dir)
    markdown_content = renderer.render()

    safe_filename = re.sub(r'[^\w\-_.]', '_', args.name)
    output_path = os.path.join(args.output_dir, f"{safe_filename}_{args.output}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"✅ Successfully generated {output_path}")
    if args.primary_name:
        print(f"👤 Aggregated under primary name: {args.primary_name}")
    
    date_range = metrics["date_range"]
    if date_range["first"] and date_range["last"]:
        print(f"📅 Period: {date_range['first'].strftime('%Y-%m-%d')} to {date_range['last'].strftime('%Y-%m-%d')} ({date_range['total_days']} days)")
    
    print(f"📊 Stats: {metrics['summary']['total_commits']} commits, +{metrics['summary']['total_insertions']}/-{metrics['summary']['total_deletions']} lines.")


if __name__ == "__main__":
    main()


# py "Folder Path/main.py" --repo "Repo Path" --name "Project Name" --author "Name 1, Name 2" --primary-name "Name to Display" --output-dir "D:\Personal\corporate_history" --output "README.md"
