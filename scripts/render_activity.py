"""Render an SVG using the dates and levels in GitHub's public calendar."""

from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


CALENDAR_URL = "https://github.com/users/coneldiablo/contributions"
ASSET = Path(__file__).resolve().parents[1] / "assets" / "contribution-signal.svg"
COLORS = ("#2a1f24", "#83404b", "#b64b54", "#ea5453", "#ffa196")
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        if tag != "td":
            return
        fields = dict(attrs)
        if not fields.get("id", "").startswith("contribution-day-component-"):
            return
        day = date.fromisoformat(fields["data-date"])
        level = int(fields["data-level"])
        if not 0 <= level < len(COLORS):
            raise ValueError(f"Unexpected contribution level: {level}")
        self.days[day] = level


def render(days):
    first, last = min(days), max(days)
    if not 360 <= len(days) <= 378 or (last - first).days + 1 != len(days):
        raise ValueError("Expected a complete year from the GitHub calendar")
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    weeks = (last - sunday).days // 7 + 1
    if not 52 <= weeks <= 54:
        raise ValueError(f"Unexpected calendar width: {weeks} weeks")

    svg = ['''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="229" viewBox="0 0 960 229" role="img" aria-labelledby="title desc">
<title id="title">Contribution calendar</title>
<desc id="desc">GitHub activity in the last year. Brighter cells indicate greater activity.</desc>
<defs>
  <clipPath id="chart"><rect x="44" y="75" width="878" height="108" rx="4"/></clipPath>
  <linearGradient id="scan">
    <stop stop-color="#ff594f" stop-opacity="0"/>
    <stop offset="1" stop-color="#ff594f" stop-opacity=".34"/>
  </linearGradient>
</defs>
<style>
  .scan { animation: sweep 4.6s linear 1 both; }
  @keyframes sweep { from { transform: translateX(0); } to { transform: translateX(960px); } }
  @media (prefers-reduced-motion: reduce) { .scan { display: none; } }
</style>
<rect x="1" y="1" width="958" height="227" rx="5" fill="#110d10" stroke="#4a333a" stroke-width="2"/>
<path d="M1 51H959M1 193H959" stroke="#402c35"/>
<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-weight="600">
  <circle cx="42" cy="26" r="4" fill="#ff645a"/>
  <text x="58" y="31" fill="#ffa59a" font-size="16" letter-spacing="2">CONTRIBUTION SIGNAL</text>
  <text x="920" y="31" text-anchor="end" fill="#e1cdd4" font-size="15" letter-spacing="2">LAST 12 MONTHS</text>''']
    column_spacing = 872 / weeks
    previous_label = -5
    for day, level in sorted(days.items()):
        column, row = divmod((day - sunday).days, 7)
        x, y = round(44 + column_spacing * column, 2), 77 + 15 * row
        if day.day == 1 and column - previous_label >= 4 and column <= weeks - 3:
            svg.append(f'<text x="{x}" y="68" fill="#e1cdd4" font-size="13">{MONTHS[day.month - 1]}</text>')
            previous_label = column
        svg.append(f'<rect x="{x}" y="{y}" width="12" height="12" rx="2" fill="{COLORS[level]}"/>')

    svg.append('''<g clip-path="url(#chart)">
  <g class="scan">
    <rect x="-36" y="75" width="80" height="108" fill="url(#scan)"/>
    <path d="M44 75V183" stroke="#ffa59a" stroke-opacity=".7"/>
  </g>
</g>''')
    svg.append(f'<text x="38" y="215" fill="#e1cdd4" font-size="11">{first:%Y.%m.%d} / {last:%Y.%m.%d}</text>')
    svg.append('<text x="775" y="215" fill="#e1cdd4" font-size="10">LESS</text>')
    for index, color in enumerate(COLORS):
        svg.append(f'<rect x="{809 + 15 * index}" y="205" width="11" height="11" rx="2" fill="{color}"/>')
    svg.append('<text x="919" y="215" text-anchor="end" fill="#e1cdd4" font-size="10">MORE</text>')
    return "\n".join([*svg, "</g>", "</svg>", ""])


if __name__ == "__main__":
    request = Request(CALENDAR_URL, headers={"User-Agent": "coneldiablo-profile-calendar"})
    with urlopen(request, timeout=30) as response:
        parser = CalendarParser()
        parser.feed(response.read().decode("utf-8"))
    if not parser.days:
        raise ValueError("GitHub returned no contribution days")
    ASSET.write_text(render(parser.days), encoding="utf-8")
    print(f"Rendered {len(parser.days)} days from the public GitHub calendar")
