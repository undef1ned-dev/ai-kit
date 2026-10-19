from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Article


def article_list(request):
    data = []
    for article in Article.objects.all():
        data.append({"id": article.id, "title": article.title, "author": article.author.username})
    return JsonResponse(data, safe=False)


def article_search(request):
    query = request.GET.get("q", "")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id, title FROM articles_article WHERE title LIKE '%{query}%'")
        rows = cursor.fetchall()
    return JsonResponse([{"id": row[0], "title": row[1]} for row in rows], safe=False)


@csrf_exempt
def article_delete(request, article_id):
    Article.objects.filter(id=article_id).delete()
    return JsonResponse({"deleted": article_id})
