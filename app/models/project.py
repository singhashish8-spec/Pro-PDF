"""In-memory markup document: the Glass Layer's object store.

Qt-agnostic on purpose so it can be unit tested and reused by the export
pipeline without importing PyQt6 (Blueprint v2, Section 6.2/6.4).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from app.models.markup import MarkupObject

ChangeListener = Callable[[], None]


@dataclass
class Calibration:
    id: str
    page_index: int
    pdf_distance: float
    real_distance: float
    unit: str = "ft"

    @property
    def scale_factor(self) -> float:
        """Real-world units per PDF user-space point."""
        if self.pdf_distance == 0:
            return 1.0
        return self.real_distance / self.pdf_distance


class MarkupDocument:
    """Holds every MarkupObject in the open project, keyed by page."""

    def __init__(self) -> None:
        self._by_page: dict[int, list[MarkupObject]] = defaultdict(list)
        self._by_id: dict[str, MarkupObject] = {}
        self._calibrations: dict[str, Calibration] = {}
        self._listeners: list[ChangeListener] = []

    # -- change notification ------------------------------------------
    def add_listener(self, listener: ChangeListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: ChangeListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    # -- markup objects --------------------------------------------------
    def add(self, obj: MarkupObject) -> None:
        self._by_page[obj.page_index].append(obj)
        self._by_id[obj.id] = obj
        self._notify()

    def remove(self, obj_id: str) -> MarkupObject | None:
        obj = self._by_id.pop(obj_id, None)
        if obj is None:
            return None
        self._by_page[obj.page_index].remove(obj)
        self._notify()
        return obj

    def get(self, obj_id: str) -> MarkupObject | None:
        return self._by_id.get(obj_id)

    def objects_on_page(self, page_index: int) -> list[MarkupObject]:
        return list(self._by_page.get(page_index, []))

    def all_objects(self) -> list[MarkupObject]:
        return list(self._by_id.values())

    def replace_all(self, objects: list[MarkupObject]) -> None:
        self._by_page.clear()
        self._by_id.clear()
        for obj in objects:
            self._by_page[obj.page_index].append(obj)
            self._by_id[obj.id] = obj
        self._notify()

    def notify_object_changed(self) -> None:
        """Call after in-place mutation of an object already in the store."""
        self._notify()

    # -- page structure changes (Section 7.4) -------------------------------
    def remove_objects_on_page(self, page_index: int) -> None:
        """Drops every object on a page being deleted."""
        for obj in self.objects_on_page(page_index):
            self.remove(obj.id)

    def shift_pages(self, from_index: int, delta: int) -> None:
        """Adjusts every object's page_index by `delta` for pages at/after
        `from_index` — call after inserting (`delta=+1`) or deleting
        (`delta=-1`) a page, once any objects on a deleted page are gone."""
        rebuilt: dict[int, list[MarkupObject]] = defaultdict(list)
        for obj in self.all_objects():
            if obj.page_index >= from_index:
                obj.page_index += delta
            rebuilt[obj.page_index].append(obj)
        self._by_page = rebuilt
        for cal in self._calibrations.values():
            if cal.page_index >= from_index:
                cal.page_index += delta
        self._notify()

    def remap_pages(self, new_order: list[int]) -> None:
        """Reassigns page_index per `new_order` (old index at each new position),
        e.g. after reordering pages — new_order[i] is the OLD index now at position i."""
        old_to_new = {old: new for new, old in enumerate(new_order)}
        for obj in self.all_objects():
            if obj.page_index in old_to_new:
                obj.page_index = old_to_new[obj.page_index]
        for cal in self._calibrations.values():
            if cal.page_index in old_to_new:
                cal.page_index = old_to_new[cal.page_index]
        rebuilt: dict[int, list[MarkupObject]] = defaultdict(list)
        for obj in self.all_objects():
            rebuilt[obj.page_index].append(obj)
        self._by_page = rebuilt
        self._notify()

    def to_journal(self) -> list[dict]:
        return [obj.to_dict() for obj in self.all_objects()]

    # -- calibrations ------------------------------------------------------
    def add_calibration(self, calibration: Calibration) -> None:
        self._calibrations[calibration.id] = calibration
        self._notify()

    def get_calibration(self, calibration_id: str) -> Calibration | None:
        return self._calibrations.get(calibration_id)

    def remove_calibration(self, calibration_id: str) -> None:
        if self._calibrations.pop(calibration_id, None) is not None:
            self._notify()

    def calibrations_for_page(self, page_index: int) -> list[Calibration]:
        return [c for c in self._calibrations.values() if c.page_index == page_index]


@dataclass
class FormField:
    id: str
    name: str
    field_type: str  # text | checkbox | radio | dropdown | date | signature
    page_index: int
    rect: tuple[float, float, float, float]
    value: str = ""
    options: list[str] = field(default_factory=list)
    required: bool = False
    validation_regex: str | None = None
