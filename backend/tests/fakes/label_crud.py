from app.models import Label
from app.utils import utcnow

from .domain import DomainStore


class FakeLabelCRUD:
    """In-memory stand-in for LabelCRUD used in unit tests."""

    def __init__(self, store: DomainStore):
        """Attach the shared in-memory tables.

        Args:
            store: shared domain tables.
        """
        self.store = store

    async def create_label(self, session, label: Label) -> Label:
        """Store a new project label and assign an id.

        Args:
            session: unused session placeholder.
            label: label to store.

        Returns:
            Label: the stored label with assigned id.
        """
        label.id = self.store.label_seq
        self.store.label_seq += 1
        label.created_at = label.created_at or utcnow()
        label.updated_at = label.updated_at or utcnow()
        self.store.labels[label.id] = label
        return label

    async def get_by_id(self, session, project_id: int, label_id: int) -> Label | None:
        """Return one label of a project.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            label_id: label id to look up.

        Returns:
            Label | None: the label or None.
        """
        label = self.store.labels.get(label_id)
        if label is None or label.project_id != project_id:
            return None
        return label

    async def get_by_name(self, session, project_id: int, name: str) -> Label | None:
        """Return one label of a project by its name, case-insensitively.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            name: label name to look up.

        Returns:
            Label | None: the label or None.
        """
        for label in self.store.labels.values():
            if label.project_id == project_id and label.name.lower() == name.lower():
                return label
        return None

    async def list_by_project(self, session, project_id: int) -> list[Label]:
        """Return all labels of a project ordered by name.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.

        Returns:
            list[Label]: labels ordered by name.
        """
        labels = [
            label
            for label in self.store.labels.values()
            if label.project_id == project_id
        ]
        labels.sort(key=lambda label: (label.name.lower(), label.id))
        return labels

    async def update(self, session, label: Label) -> Label:
        """Flush pending changes of a label row.

        Args:
            session: unused session placeholder.
            label: label to flush.

        Returns:
            Label: the same label instance.
        """
        return label

    async def delete(self, session, label: Label) -> None:
        """Delete a label row.

        Args:
            session: unused session placeholder.
            label: label to delete.
        """
        self.store.labels.pop(label.id, None)
