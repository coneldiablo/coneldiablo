"""Update profile cards from the public GitHub API."""
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"

def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path], text=True))

def graphql(query):
    return json.loads(subprocess.check_output(["gh", "api", "graphql", "-f", f"query={query}"], text=True))

def frame(title, subtitle, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="440" height="230" viewBox="0 0 440 230" role="img" aria-label="{escape(title)}">
<rect x="1" y="1" width="438" height="228" rx="16" fill="#09090B" stroke="#27272A"/>
<g font-family="ui-monospace,Menlo,Consolas,monospace">
<text x="26" y="37" fill="#FAFAFA" font-size="18" font-weight="700">{title}</text>
<text x="26" y="59" fill="#A1A1AA" font-size="11">{subtitle}</text>
{body}</g></svg>'''

user = api("users/coneldiablo")
repos = []
page = 1
while True:
    batch = api(f"users/coneldiablo/repos?per_page=100&page={page}")
    repos.extend(r for r in batch if not r["private"])
    if len(batch) < 100:
        break
    page += 1
owned = [r for r in repos if not r["fork"]]
today = datetime.now(timezone.utc).strftime("%d %b %Y")
metrics = [(len(owned), "Original repositories"), (sum(r["stargazers_count"] for r in owned), "Stars on original repos"),
           (user["followers"], "Followers"), (len(repos)-len(owned), "Forks")]
body = ""
for i, (value, label) in enumerate(metrics):
    x, y = 26 + (i % 2) * 210, 110 + (i // 2) * 79
    body += f'<text x="{x}" y="{y}" fill="#FAFAFA" font-size="32" font-weight="700">{value}</text><text x="{x}" y="{y+22}" fill="#A1A1AA" font-size="12">{label}</text>'
(ASSETS / "stats.svg").write_text(frame("GitHub overview", f"Public profile · updated {today}", body))
langs = Counter(r["language"] for r in owned if r["language"])
colors = ["#FAFAFA", "#D4D4D8", "#A1A1AA", "#71717A", "#52525B"]
body = ""
for i, (language, count) in enumerate(langs.most_common(5)):
    y = 88 + i * 28
    body += f'<circle cx="30" cy="{y-4}" r="4" fill="{colors[i]}"/><text x="43" y="{y}" fill="#E4E4E7" font-size="12">{escape(language)}</text><rect x="145" y="{y-10}" width="235" height="8" rx="4" fill="#27272A"/><rect x="145" y="{y-10}" width="{235*count/sum(langs.values()):.1f}" height="8" rx="4" fill="{colors[i]}"/><text x="410" y="{y}" fill="#A1A1AA" font-size="12" text-anchor="end">{count}</text>'
(ASSETS / "languages.svg").write_text(frame("Languages across projects", "Original public repos · counted by primary language", body))

def relative_time(iso):
    delta = datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 1)} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h ago"
    days = hours // 24
    if days < 30:
        return f"{days} d ago"
    return f"{days // 30} mo ago"

def wrap(text, width):
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines[:2]

active = sorted(
    (r for r in owned if r["name"] != "coneldiablo"),
    key=lambda r: r["pushed_at"],
    reverse=True,
)
commit_lines = [
    '<text x="26" y="90" fill="#71717A" font-size="12">$ git log -1 --oneline</text>',
]
if active:
    repo = active[0]
    commit = api(f"repos/{repo['full_name']}/commits?per_page=1")[0]
    message = commit["commit"]["message"].splitlines()[0]
    sha = commit["sha"][:7]
    commit_lines.append(f'<text x="26" y="115" fill="#D4D4D8" font-size="13">{escape(repo["name"])} <tspan fill="#52525B">@ {sha}</tspan></text>')
    for i, line in enumerate(wrap(message, 46)):
        commit_lines.append(f'<text x="26" y="{139 + i * 19}" fill="#FAFAFA" font-size="14" font-weight="700">{escape(line)}</text>')
    commit_lines.append(f'<text x="26" y="195" fill="#71717A" font-size="11">{relative_time(commit["commit"]["author"]["date"])}</text>')
else:
    commit_lines.append('<text x="26" y="115" fill="#71717A" font-size="13">No recent activity</text>')
(ASSETS / "live.svg").write_text(frame("Last shipped", "Most recent commit, fetched live", "\n".join(commit_lines)))

contrib = graphql('''{
  user(login: "coneldiablo") {
    createdAt
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}''')["data"]["user"]

created = datetime.fromisoformat(contrib["createdAt"].replace("Z", "+00:00"))
years_active = max((datetime.now(timezone.utc) - created).days / 365.25, 0.1)
cc = contrib["contributionsCollection"]
milestones = [
    (f"{years_active:.1f}y", "On GitHub since"),
    (cc["contributionCalendar"]["totalContributions"], "Contributions (12 mo)"),
    (cc["totalPullRequestContributions"], "Pull requests opened"),
    (cc["totalIssueContributions"], "Issues opened"),
]
body = ""
for i, (value, label) in enumerate(milestones):
    x, y = 26 + (i % 2) * 210, 110 + (i // 2) * 79
    body += f'<text x="{x}" y="{y}" fill="#FAFAFA" font-size="32" font-weight="700">{value}</text><text x="{x}" y="{y+22}" fill="#A1A1AA" font-size="12">{label}</text>'
(ASSETS / "trophies.svg").write_text(frame("Milestones", "Computed live from the public contribution graph", body))

weeks = contrib["contributionsCollection"]["contributionCalendar"]["weeks"]
totals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
peak = max(totals) or 1
bar_w, gap, left, top, chart_h = 12, 4, 20, 20, 110
width = left * 2 + len(totals) * (bar_w + gap)
bars = ""
for i, count in enumerate(totals):
    h = 6 if count == 0 else round(6 + (count / peak) * (chart_h - 6))
    x = left + i * (bar_w + gap)
    y = top + chart_h - h
    shade = "#27272A" if count == 0 else ("#FAFAFA" if count == peak else "#71717A")
    bars += f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" rx="2" fill="{shade}"/>'
activity_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="170" viewBox="0 0 {width} 170" role="img" aria-label="Weekly contributions over the last year">
<rect width="{width}" height="170" rx="16" fill="#09090B"/>
<g font-family="ui-monospace,Menlo,Consolas,monospace">
<text x="{left}" y="18" fill="#A1A1AA" font-size="12">52-week contribution rhythm · peak week {peak}</text>
{bars}
</g></svg>'''
(ASSETS / "activity.svg").write_text(activity_svg)

print(f"Updated cards using {len(repos)} public repositories")
