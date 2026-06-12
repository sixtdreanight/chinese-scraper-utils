"""chinese-scraper-utils — 统一错误类型体系。

对标 httpx 的分层设计，让调用方可以按类型处理错误。

Usage:
    from chinese_scraper_utils.errors import ScraperError, RateLimitError

    try:
        events = scrape_weibo_hot()
    except RateLimitError:
        await asyncio.sleep(60)
    except ScraperError as e:
        logger.error("Scrape failed: %s", e)
"""


class ScraperError(Exception):
    """抓取基础异常。所有抓取相关错误的基类。"""
    pass


class RateLimitError(ScraperError):
    """请求被限流（HTTP 429 或触发平台反爬机制）。"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ExtractionError(ScraperError):
    """LLM 提取失败（API 调用失败、返回格式异常）。"""
    def __init__(self, message: str = "Extraction failed", raw_response: str | None = None):
        super().__init__(message)
        self.raw_response = raw_response


class ValidationError(ScraperError):
    """数据校验失败（日期/城市/类别不在预期范围内）。"""
    def __init__(self, message: str = "Validation failed", field: str = "", value: str = ""):
        super().__init__(message)
        self.field = field
        self.value = value


class NetworkError(ScraperError):
    """网络请求错误（超时、DNS、连接被拒）。"""
    def __init__(self, message: str = "Network error", url: str = ""):
        super().__init__(message)
        self.url = url


class CircuitBreakerOpen(ScraperError):  # noqa: N818
    """熔断器已打开 — API 调用被阻止，等待恢复超时到期。"""
    def __init__(self, message: str = "Circuit breaker is open", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after
