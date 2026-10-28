# Cybersecurity Skills Integration Guide

Your DesktopPet CLI now includes access to **754 cybersecurity skills** from the Anthropic-Cybersecurity-Skills repository, with both command-line browsing and LLM integration.

## Quick Start

### 1. Sync Skills (First Time)
```bash
pet skills sync
```
Downloads and caches all 754 skills locally (~20MB). Run this once to populate your local index.

### 2. Browse Skills

**List all skills:**
```bash
pet skills list
```

**List skills in a domain:**
```bash
pet skills list --domain "Cloud Security"
```

**Search by keyword, topic, or tag:**
```bash
pet skills search "malware analysis"
pet skills search "AWS"
pet skills search "forensics"
```

**View full skill workflow:**
```bash
pet skills show analyzing-android-malware-with-apktool
```

## Using Skills in Chat

When you chat with the companion, it can search and recommend relevant skills:

```
You: "How do I analyze Android malware?"

Companion: [searches for related skills]
Found: analyzing-android-malware-with-apktool
       analyzing-android-app-reverse-engineering
       ...
I recommend the "analyzing-android-malware-with-apktool" skill.
To see the full workflow, run: pet skills show analyzing-android-malware-with-apktool
```

## Skill Structure

Each skill includes:
- **Name** — kebab-case identifier
- **Description** — one-line summary
- **Domain** — broad category (all currently "cybersecurity")
- **Tags** — keywords for searching
- **Author** — skill creator
- **Workflow** — step-by-step procedures
- **Prerequisites** — tools and permissions needed
- **Examples** — real-world scenarios

## Behind the Scenes

**Storage:**
- Index: `~/.local/share/desktop_pet/skills/index.json` (754 skill metadata)
- Cache: `~/.local/share/desktop_pet/skills/cache/` (downloaded skill details)

**Available Tools in Chat:**
- `search_skills` — LLM can call this to find skills programmatically

## Skill Domains

Currently all 754 skills are categorized under "cybersecurity" with specializations including:
- Malware Analysis
- Forensics & Incident Response
- Cloud Security
- Network Security
- Web Application Security
- Threat Intelligence
- And many more...

## Examples

```bash
# Find skills about specific tools
pet skills search "Wireshark"
pet skills search "Ghidra"
pet skills search "Burp Suite"

# Find skills by technique
pet skills search "privilege escalation"
pet skills search "lateral movement"
pet skills search "data exfiltration"

# Get the full workflow for execution
pet skills show analyzing-network-traffic-with-wireshark
```

## Updating Skills

Skills are cached locally. To refresh from the repository:
```bash
pet skills sync
```

This re-downloads the index and updates any locally cached skills.
