"""业务异常：统一转换为中文错误响应。"""


class BusinessError(Exception):
    """带 HTTP 状态码与中文提示的业务异常。"""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
