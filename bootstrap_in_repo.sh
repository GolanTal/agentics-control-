#!/usr/bin/env bash
set -euo pipefail

# folders
mkdir -p control/{prompts,sops,rubrics,playbooks,templates} agents scripts .github/workflows

# housekeeping
cat > .gitignore <<'EOF'
.DS_Store
__pycache__/
*.pyc
.env*
EOF

cat > README.md <<'EOF'
# Agentics (single-repo)
Prompts/SOPs/rubrics + lightweight agent scripts and a scheduler.
Human-in-the-loop review (CXO + Red Team) before publishing.
EOF

# ---------- CONTROL ----------
cat > control/prompts/quote_hunter.md <<'EOF'
Gather 20 quote candidates (manuscript + author-original; external only with explicit permission).
Tag theme/tone/length/platform. Record source & location. Do not fabricate.
EOF

cat > control/prompts/cxo.md <<'EOF'
Score 0–3 on 10 criteria (hook, voice, usefulness, structure, CTA, proof/consent,
save/share, completion, novelty, compliance). Pass ≥24/30. Enforce truth/consent rule.
EOF

cat > control/prompts/red_team.md <<'EOF'
Block risky claims or missing proof/consent. Propose fixes. No policy violations.
EOF

cat > control/prompts/analyst.md <<'EOF'
Read KPIs from the Control Sheet. Output one-pager + 3 recommendations + next-week A/B matrix.
EOF

cat > control/sops/utm_schema.md <<'EOF'
utm_source={platform}&utm_medium={format}&utm_campaign={weekly_theme}&utm_content={variant}
EOF

cat > control/playbooks/weekly_operating_rhythm.md <<'EOF'
Mon: OKRs+theme→briefs→drafts→CXO/RedTeam→schedule.
Daily: 1 short + 1 text; 2× engagement windows.
Fri: analytics one-pager → pick winners → set next tests → Forge decisions.
EOF

cat > control/rubrics/cxo_rubric_quotes.csv <<'EOF'
criterion,description
Hook clarity,Instantly understandable and specific
Voice & brand,Matches tone rules; consistent capitalization
Usefulness,Delivers value: insight or practice
Structure,Hook → beats → CTA, clean flow
CTA quality,One clear next step, relevant
Proof/consent,Claims cited; consents recorded as needed
Save/share potential,Likely to be saved/shared
Completion,Links and UTMs present; nothing missing
Novelty,Not a repeat of last week’s winners
Compliance & access,Policy-safe; captions and alt text present
EOF

# templates to import into Google Sheets
cat > control/templates/quotes_backlog_template.csv <<'EOF'
quote_id,source_type,quote_text,source_reference,location,theme,tone_tag,length_category,platform_fit,owner,consent_status,paraphrase_ok,status,notes
Q-0001,book_internal,We are one.,The New World: The Key,Prologue,Awakening,uplifting,ultra_short,"IG,TikTok,Shorts,X",Architect,not_needed,yes,collected,
Q-0002,author_original,Clarity is a muscle, not a mood.,Author original,,Clarity,pragmatic,ultra_short,"IG,TikTok,Shorts,X,LI",Architect,not_needed,yes,collected,
Q-0003,external_with_permission,,,URL or contact,Community,social_proof,short,"IG,LI,X",Community,requested,no,pending,Add consent proof link
EOF

cat > control/templates/quotes_ab_test_template.csv <<'EOF'
test_id,quote_id,variant,visual_format,caption_baseline,cta,platforms,schedule_date,utm_content,sample_size_goal,win_metric,win_threshold,fallback_rule,status
T-001,Q-0002,A,face_cam_overlay,"Tell the story of choosing clarity once.",Read the book,"IG,TikTok,Shorts",,hookCM1,"1500 impressions",3s_view_pct,">=30%","If below, try text-over-broll",planned
T-001,Q-0002,B,text_over_broll,"Same caption; only hook style changes.",Read the book,"IG,TikTok,Shorts",,hookCM1B,"1500 impressions",3s_view_pct,">=30%","If below, test question form",planned
T-002,Q-0001,A,quote_card,"Short reflection + one practice.",Get the companion,"IG,LI,X",,hookQ1A,"100 link clicks",save_share_per_1k,">=5","Swap CTA to book if saves>8",planned
EOF

cat > control/templates/hitl_review_checklist.md <<'EOF'
# HITL Review — Quotes & Hook Posts
Policy: no fabricated quotes/reviews. Claims need proof; external quotes need consent.

1) Attribution/Consent ✔ source set; consent linked if external; paraphrase_ok respected
2) Brand/Voice ✔ plain tone; no em dashes; capitalization consistent
3) Platform Fit ✔ aspect ratio; captions; alt text
4) Safety/Claims ✔ proof attached; no policy risks; single clear CTA
5) UTM & Scheduling ✔ UTMs filled; approved slot; CXO score ≥24/30
EOF

# ---------- AGENTS (stubs) ----------
cat > agents/quote_hunter.py <<'EOF'
print("quote_hunter: ok — stub (connect to Google Sheets to collect/tag quotes).")
EOF

cat > agents/variant_generator.py <<'EOF'
print("variant_generator: ok — stub (build face-cam overlay / quote-card / b-roll scripts).")
EOF

cat > agents/channel_mapper.py <<'EOF'
print("channel_mapper: ok — stub (map variants to IG/TikTok/Shorts/X/LinkedIn).")
EOF

cat > agents/analyst.py <<'EOF'
print("analyst: ok — stub (read KPIs, output one-pager + next-week tests).")
EOF

# ---------- Scripts ----------
cat > scripts/run_pipeline.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
python agents/quote_hunter.py
python agents/variant_generator.py
python agents/channel_mapper.py
EOF
chmod +x scripts/run_pipeline.sh

# ---------- Python deps + GitHub Actions workflow ----------
cat > requirements.txt <<'EOF'
gspread
google-auth
pandas
EOF

cat > .github/workflows/scheduler.yml <<'EOF'
name: agentics-scheduler
on:
  schedule:
    - cron: "0 13 * * 1"    # Mon plan
    - cron: "0 14 * * 1-5"  # Weekdays content
    - cron: "0 21 * * 5"    # Fri report
  workflow_dispatch:
jobs:
  daily_content:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - name: Run pipeline
        run: scripts/run_pipeline.sh
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          CONTROL_SHEET_ID: ${{ secrets.CONTROL_SHEET_ID }}
  weekly_report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - name: Build analytics one-pager
        run: python agents/analyst.py
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          CONTROL_SHEET_ID: ${{ secrets.CONTROL_SHEET_ID }}
EOF

# commit
git add .
git commit -m "Bootstrap agentics tree (control + agents + workflow)"
