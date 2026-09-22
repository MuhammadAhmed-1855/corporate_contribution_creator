#!/usr/bin/env python3
"""
Git Contribution README Generator (NDA-Safe, Raw Metadata)
Generates comprehensive README files in a central output directory.
"""

import subprocess
import re
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import argparse
import sys


class GitMetricsExtractor:
    """Phase 1: Extract and calculate all raw metrics from Git."""

    def __init__(self, repo_path=".", author_filters=None):
        self.repo_path = repo_path
        # Normalize filters to lowercase for case-insensitive matching
        self.author_filters = [f.strip().lower() for f in author_filters] if author_filters else []
        self.commits = []
        self.file_stats = []

    def _run_git(self, args):
        """Execute git command safely."""
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
        """List all unique authors with commit counts."""
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
        
        print(f"📊 Found {len(author_counts)} unique author(s):\n")
        print(f"{'Author':<55} {'Commits':<10}")
        print("-" * 65)
        
        for author, count in author_counts.most_common():
            print(f"{author:<55} {count:<10}")
        
        print(f"\n💡 Tip: Use --author with a comma-separated list of your aliases.")
        print(f"   Example: --author \"MuhammadAhmed_Dev, Muhammad Ahmed, hussain\"")

    def extract_all_data(self):
        """Main extraction pipeline."""
        print("🔍 Extracting raw commit metadata...")
        self._extract_commits_and_numstat()

        print("🧮 Calculating advanced metrics...")
        metrics = {
            "summary": self._calc_summary(),
            "timeline": self._calc_timeline(),
            "streaks": self._calc_streaks(),
            "time_analysis": self._calc_time_analysis(),
            "languages": self._calc_languages(),
            "top_files": self._calc_top_files(),
            "raw_commits": self.commits
        }
        return metrics

    def _is_my_commit(self, author_name, author_email):
        """Check if the commit belongs to any of the specified author filters."""
        if not self.author_filters:
            return True  # No filter = include everyone
        
        name_lower = author_name.lower()
        email_lower = author_email.lower()
        
        # Match if ANY filter is a substring of the name or email
        return any(f in name_lower or f in email_lower for f in self.author_filters)

    def _extract_commits_and_numstat(self):
        """Extract commit info and file changes in a single pass."""
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
                    current_commit["files"].append({
                        "path": filepath,
                        "adds": adds,
                        "dels": dels
                    })

                    self.file_stats.append({
                        "path": filepath,
                        "adds": adds,
                        "dels": dels,
                        "date": current_commit["date"]
                    })

        # Don't forget the last commit!
        if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
            self.commits.append(current_commit)

    def _calc_summary(self):
        total_commits = len(self.commits)
        total_adds = sum(c["insertions"] for c in self.commits)
        total_dels = sum(c["deletions"] for c in self.commits)
        total_files_touched = len(set(f["path"] for f in self.file_stats))

        # Even though we filtered, we show the original aliases in the summary for transparency
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

        return {
            "days_of_week": dict(day_counts),
            "hours_of_day": dict(hour_counts)
        }

    def _calc_languages(self):
        ext_counts = Counter()
        for f in self.file_stats:
            ext = os.path.splitext(f["path"])[1].lower()
            if ext:
                ext_counts[ext] += 1
        return dict(ext_counts.most_common(10))

    def _calc_top_files(self):
        file_commit_counts = Counter(f["path"] for f in self.file_stats)
        return dict(file_commit_counts.most_common(10))


class MarkdownRenderer:
    """Phase 2: Render the extracted metrics into a beautiful README.md."""

    def __init__(self, metrics, repo_name="Project", primary_name=None):
        self.metrics = metrics
        self.repo_name = repo_name
        self.primary_name = primary_name

    def render(self):
        md = []
        md.append(self._render_header())
        md.append(self._render_summary_table())
        md.append(self._render_heatmap())
        md.append(self._render_time_analysis())
        md.append(self._render_languages_and_files())
        md.append(self._render_recent_commits())
        md.append(self._render_footer())

        return "\n\n".join(md)

    def _render_header(self):
        author_info = f" | Author: `{self.primary_name}` (Aggregated aliases)" if self.primary_name else ""
        return (
            f"# 📊 {self.repo_name} - Contribution Metrics\n\n"
            f"*Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Raw metadata, zero code diffs.{author_info}*"
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

    def _render_heatmap(self):
        timeline = self.metrics["timeline"]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=364)
        days_to_monday = start_date.weekday()
        grid_start = start_date - timedelta(days=days_to_monday)

        grid = [["░" for _ in range(53)] for _ in range(7)]
        current = grid_start
        
        for week in range(53):
            for day in range(7):
                date_str = current.strftime("%Y-%m-%d")
                count = timeline.get(date_str, 0)

                if count == 0: block = "░"
                elif count == 1: block = "▒"
                elif count <= 3: block = "▓"
                else: block = "█"

                grid[day][week] = block
                current += timedelta(days=1)

        days_label = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        heatmap_text = "```\n"
        for i, row in enumerate(grid):
            heatmap_text += f"{days_label[i]} {''.join(row)}\n"
        heatmap_text += "```\n*Legend: `░` 0 | `▒` 1 | `▓` 2-3 | `█` 4+*"

        return f"## 🟩 Contribution Heatmap (Last 52 Weeks)\n\n{heatmap_text}"

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
            "## 🕒 Time Analysis\n\n"
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
    parser = argparse.ArgumentParser(
        description="Generate comprehensive NDA-safe README files in a central directory."
    )
    parser.add_argument("--repo", required=True, help="Path to the git repository to analyze")
    parser.add_argument("--output-dir", default="D:\\Personal\\corporate_history", 
                       help="Directory to save README files")
    parser.add_argument("--name", default=None, help="Project name (used as filename)")
    parser.add_argument("--author", default=None, 
                       help="Comma-separated list of author names/emails to include (e.g., 'MuhammadAhmed_Dev, Muhammad Ahmed, hussain')")
    parser.add_argument("--primary-name", default=None, 
                       help="The clean name to display in the README header (e.g., 'Muhammad Ahmed')")
    parser.add_argument("--list-authors", action="store_true", help="List all authors in the repository and exit")
    parser.add_argument("--output", default="README.md", help="Output filename")

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # Parse comma-separated authors into a list
    author_filters = [a.strip() for a in args.author.split(',')] if args.author else None

    extractor = GitMetricsExtractor(repo_path=args.repo, author_filters=author_filters)
    
    if args.list_authors:
        extractor.list_all_authors()
        sys.exit(0)
    
    if not args.name:
        print("❌ Error: --name is required when generating README")
        sys.exit(1)
    
    metrics = extractor.extract_all_data()

    if metrics["summary"]["total_commits"] == 0:
        print("⚠️ No commits found matching your author filters.")
        print(f"   Filters used: {args.author}")
        print(f"\n💡 Run with --list-authors to see exact spelling of all authors.")
        sys.exit(0)

    renderer = MarkdownRenderer(metrics, repo_name=args.name, primary_name=args.primary_name)
    markdown_content = renderer.render()

    safe_filename = re.sub(r'[^\w\-_.]', '_', args.name)
    output_path = os.path.join(args.output_dir, f"{safe_filename}_{args.output}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"✅ Successfully generated {output_path}")
    if args.primary_name:
        print(f"👤 Aggregated under primary name: {args.primary_name}")
    print(f"📊 Stats: {metrics['summary']['total_commits']} commits, +{metrics['summary']['total_insertions']}/-{metrics['summary']['total_deletions']} lines.")


if __name__ == "__main__":
    main()


# py "Folder Path/main.py" --repo "Repo Path" --name "Project Name" --author "Name 1, Name 2" --primary-name "Name to Display" --output-dir "D:\Personal\corporate_history" --output "README.md"
