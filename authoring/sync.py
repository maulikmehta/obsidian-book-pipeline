import os
import re

def clean_text(text):
    # Strip frontmatter
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    # Strip wikilinks [[Name]] -> Name
    text = re.sub(r"\[\[([^|\]]+?)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) if m.group(2) else m.group(1), text)
    # Strip the ::: fence TOKENS only - never the line they sit on. The old
    # pattern ran to the newline, so an inline `::: {.letter}Sentence. :::`
    # lost its whole sentence, and this check then reported an 11-word
    # divergence in a chapter whose prose is identical in both sources.
    text = re.sub(r":::\s*\{[^}]*\}", " ", text)
    text = text.replace(":::", " ")
    # Scene separators, in every form the two pipelines have used
    text = re.sub(r"(?m)^\s*(\*\s*){3,}\s*$", " ", text)
    text = re.sub(r"(?m)^\s*-{3,}\s*$", " ", text)
    text = re.sub(r"[\u2014\u2013]{3,}[\u2014\u2013-]*", " ", text)
    # Emphasis is formatting, not words: *word* and **word** are the same prose
    text = re.sub(r"\*{1,3}", "", text)
    # Strip markdown headers if any remaining
    text = re.sub(r"(?m)^#+.*$", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def run():
    # Check page staleness
    out_path = os.path.join("Strategy", "creative", "skeleton.html")
    if os.path.exists(out_path):
        from authoring import config
        with open(out_path, "r", encoding="utf-8") as f:
            m = re.search(r'<meta name="kit-version" content="([^"]+)">', f.read())
        if not m or m.group(1) != config.KIT_VERSION:
            print(f"WARN: Strategy/creative/skeleton.html predates kit version {config.KIT_VERSION}.")
    
    if not os.path.exists("manuscript.md"):
        print("No manuscript.md found.")
        return 0

    with open("manuscript.md") as f:
        manu = f.read()

    # Split manuscript by ## Chapter
    chapters = re.split(r"(?m)^## Chapter\b", manu)
    if len(chapters) < 2:
        print("No chapters found in manuscript.md.")
        return 0

    manu_chaps = {}
    for ch in chapters[1:]:
        lines = ch.split("\n")
        title_line = lines[0].strip()
        num_match = re.match(r"(\d+)", title_line)
        if num_match:
            num = num_match.group(1)
            content = "\n".join(lines[1:])
            # bounded by ### About the Author
            content = re.split(r"(?m)^### About the Author\b", content)[0]
            manu_chaps[int(num)] = clean_text(content)

    # Read Story/ files
    if not os.path.isdir("Story"):
        print("No Story directory found.")
        return 0

    story_files = [f for f in os.listdir("Story") if re.search(r"Chapter-\d+\.md$", f)]
    if not story_files:
        print("No chapter files found in Story/.")
        return 0

    diverged = 0
    for fname in sorted(story_files):
        num_match = re.search(r"Chapter-(\d+)\.md$", fname)
        if not num_match:
            continue
        num = int(num_match.group(1))
        
        with open(os.path.join("Story", fname)) as f:
            story_content = clean_text(f.read())
            
        if num not in manu_chaps:
            continue
            
        mc = manu_chaps[num]
        sc = story_content
        
        if mc == sc:
            print(f"ch {num:<2} identical")
        else:
            diverged += 1
            wd_mc = len(mc.split())
            wd_sc = len(sc.split())
            delta = wd_mc - wd_sc
            sign = "+" if delta > 0 else ""
            print(f"ch {num:<2} {sign}{delta} words")
            
            # Find first differing phrase
            mc_words = mc.split()
            sc_words = sc.split()
            for i in range(min(len(mc_words), len(sc_words))):
                if mc_words[i] != sc_words[i]:
                    start = max(0, i - 5)
                    end_m = min(len(mc_words), i + 6)
                    end_s = min(len(sc_words), i + 6)
                    mc_context = " ".join(mc_words[start:end_m])
                    sc_context = " ".join(sc_words[start:end_s])
                    print(f"  manuscript : ... {mc_context} ...")
                    print(f"  story      : ... {sc_context} ...")
                    break
    
    return 1 if diverged else 0
