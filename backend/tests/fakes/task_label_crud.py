from app.models import TaskLabel

from .domain import DomainStore


class FakeTaskLabelCRUD:
    """In-memory stand-in for TaskLabelCRUD used in unit tests."""

    def __init__(self, store: DomainStore):
        """Attach the shared in-memory tables.

        Args:
            store: shared domain tables.
        """
        self.store = store

    async def attach(self, session, relation: TaskLabel) -> TaskLabel:
        """Store a new task label attachment.

        Args:
            session: unused session placeholder.
            relation: attachment to store.

        Returns:
            TaskLabel: the stored attachment with assigned id.
        """
        relation.id = relation.id or len(self.store.task_labels) + 1
        self.store.task_labels[(relation.task_id, relation.label_id)] = relation
        return relation

    async def get(self, session, task_id: int, label_id: int) -> TaskLabel | None:
        """Return one task label attachment.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.
            label_id: label to look for.

        Returns:
            TaskLabel | None: the attachment or None.
        """
        return self.store.task_labels.get((task_id, label_id))

    async def list_for_task(self, session, task_id: int) -> list[TaskLabel]:
        """Return all label attachments of a task.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.

        Returns:
            list[TaskLabel]: attachments with their labels loaded.
        """
        relations = [
            relation
            for relation in self.store.task_labels.values()
            if relation.task_id == task_id
        ]
        relations.sort(key=lambda relation: relation.label_id)
        for relation in relations:
            relation.label = self.store.labels.get(relation.label_id)
        return relations

    async def detach(self, session, relation: TaskLabel) -> None:
        """Delete one task label attachment.

        Args:
            session: unused session placeholder.
            relation: attachment to delete.
        """
        self.store.task_labels.pop((relation.task_id, relation.label_id), None)

    async def delete_for_label(self, session, label_id: int) -> None:
        """Delete every attachment of one label.

        Args:
            session: unused session placeholder.
            label_id: label being removed from the project.
        """
        for key in [
            key
            for key, relation in self.store.task_labels.items()
            if relation.label_id == label_id
        ]:
            self.store.task_labels.pop(key, None)
