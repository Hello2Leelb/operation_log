import abc
import functools
import ipaddress
import logging
import time
import typing


class Operator:
    def __init__(self, operator_id: int, operator_name: str, operator_ip: typing.Optional[str] = None):
        self.id: int = operator_id
        self.name: str = operator_name
        self.ip: str = operator_ip if operator_ip else ''

        if self.ip:
            # Check self.operator_ip is an ip str
            ipaddress.ip_address(self.ip)


class OperationLog:
    def __init__(self, operator: Operator, text: str, category: typing.Optional[int]):
        self.operator: Operator = operator
        self.text: str = text
        self.category: int = category if category else 0
        self.timestamp: int = int(time.time())


class OperationLogWriter(abc.ABC):
    @abc.abstractmethod
    def write(self, operation_log: OperationLog):
        pass


class DefaultOperationLogWriter(OperationLogWriter):
    def __init__(self):
        super().__init__()

    def write(self, operation_log: OperationLog):
        logging.info(
            f'operator id {operation_log.operator.id} '
            f'operator name {operation_log.operator.name} '
            f'operator ip {operation_log.operator.ip} '
            f'category {operation_log.category} '
            f'text {operation_log.text} '
            f'timestamp {operation_log.timestamp}'
        )


class OperationFailedError(Exception):
    """An error related to the operation failed"""

    def __init__(self, reason: str, execute_result: typing.Any = None):
        super().__init__(reason)

        self.reason = reason
        self.execute_result = execute_result


def record_operation_log(
        get_operator: typing.Callable[..., Operator],
        success_text: str,
        fail_text: typing.Optional[str] = None,
        category: typing.Optional[int] = None,
        before_execute_contexts: typing.Optional[typing.List[typing.Callable[..., typing.Dict]]] = None,
        after_execute_contexts: typing.Optional[typing.List[typing.Callable[..., typing.Dict]]] = None,
        writer: typing.Optional[OperationLogWriter] = None,
) -> typing.Callable:
    writer = writer if writer else DefaultOperationLogWriter()

    def decorator(func: typing.Callable[..., typing.Awaitable]) -> typing.Callable[..., typing.Awaitable]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> typing.Any:
            context = {
                'execute_success': True,
                'failed_reason': ''
            }

            operator = get_operator(*args, **kwargs)

            if before_execute_contexts:
                for before_execute_context in before_execute_contexts:
                    context.update(before_execute_context(*args, **kwargs))

            try:
                execute_result = await func(*args, **kwargs)
            except OperationFailedError as err:
                execute_result = err.execute_result

                context['execute_success'] = False
                context['failed_reason'] = err.reason

            if after_execute_contexts:
                for after_execute_context in after_execute_contexts:
                    context.update(after_execute_context(*args, **kwargs))

            operation_text_formatter = success_text if context['execute_success'] or fail_text is None else fail_text
            operation_text = operation_text_formatter.format_map(context)
            operation_log = OperationLog(operator, operation_text, category)

            writer.write(operation_log)

            return execute_result

        return wrapper

    return decorator
