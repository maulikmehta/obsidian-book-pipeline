# StoryArc

StoryArc is a medium-neutral structural visualization tool: consumes a structured authoring contract, renders a visual skeleton mapping duration, intensity, and key (e.g., emotional rasa).

## Usage

Typically invoked by the authoring toolkit (`cli.py skeleton`) during pre-production, to balance pacing and emotional beats before drafting begins.

## Files

- `main.py`: The core generator. Reads `Story/` contents and outputs `Strategy/creative/skeleton.html`.
- `templates/`: Contains `skeleton-template.html`, the visual HTML shell into which the structural data is injected.
