"""Entirely synthetic data: safe to put in a public demo or screen recording."""
from pathlib import Path

SAMPLE_FILES = {
    "note_001.txt": "Could you confirm the customer transferred the outstanding amount for our October shipment? Please attach the bank acknowledgment to the billing record.",
    "note_002.txt": "The quarterly expense claims need to be checked against our purchase slips before the tax return is prepared.",
    "note_003.txt": "The backlog needs grooming before tomorrow's standup. Assign the authentication bug to the next sprint and schedule the release review.",
    "note_004.txt": "Client asked us to confirm the app's new dashboard requirements, review the pull request, and revise the release plan.",
    "note_005.txt": "The dentist requested a follow-up consultation in two weeks. Bring the medication details and previous clinic report.",
    "note_006.txt": "After the check-up, the physician recommended returning next month to discuss the test results and treatment plan.",
    "note_007.txt": "My revision notes from the statistics lecture cover variance, probability distributions and how to prepare for the final examination.",
    "note_008.txt": "A practical tutorial on training a text classifier. Study the dataset split and learn how to assess precision and recall.",
    "note_009.txt": "Pack chargers, passports, and spare clothes for our family holiday. Also plan the grocery stop before departure.",
    "note_010.txt": "Remember to buy rice, vegetables and household cleaning supplies after picking up the birthday present.",
    "note_011.txt": "Please review this generic reminder later. It might relate to another note, but the subject isn't clear.",
}
# Reference labels used only for evaluation, never read by the sorter.
EXPECTED = {
    "note_001.txt": "Finance", "note_002.txt": "Finance",
    "note_003.txt": "Work", "note_004.txt": "Work",
    "note_005.txt": "Health", "note_006.txt": "Health",
    "note_007.txt": "Learning", "note_008.txt": "Learning",
    "note_009.txt": "Personal", "note_010.txt": "Personal",
    "note_011.txt": None,
}

def create_demo(root: Path) -> tuple[Path, Path, int]:
    inbox, organized = root / "inbox", root / "organized"
    inbox.mkdir(parents=True, exist_ok=True)
    organized.mkdir(parents=True, exist_ok=True)
    count = 0
    for name, content in SAMPLE_FILES.items():
        file = inbox / name
        if not file.exists():
            file.write_text(content, encoding="utf-8")
            count += 1
    return inbox, organized, count
