from ninja import Router

from apps.news import services
from apps.news.schemas import NewsCollectIn, NewsCollectOut

router = Router()


@router.post("/collect/", response=NewsCollectOut)
def collect_news(request, payload: NewsCollectIn):
    return services.collect_news(
        stock_codes=payload.stock_codes,
        limit=payload.limit,
    )
