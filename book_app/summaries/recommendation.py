from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import pandas as pd
from .models import Book, UserActivity
import logging

logger = logging.getLogger(__name__)

def get_recommendations(user_id):
    books = Book.objects.all()
    book_df = pd.DataFrame(list(books.values('id', 'title', 'author', 'sentiment', 'content', 'categories')))
    if book_df.empty:
        return []

    book_df['metadata'] = (
        book_df['title'].fillna('').astype(str) + ' ' +
        book_df['author'].fillna('').astype(str) + ' ' +
        book_df['categories'].fillna('').astype(str) + ' ' +
        book_df['content'].fillna('').astype(str)
    )
    book_df = book_df[book_df['metadata'].str.strip() != '']
    book_df['sentiment'] = book_df['sentiment'].fillna(0.5)

    tfidf = TfidfVectorizer(stop_words='english', max_features=5000)
    tfidf_matrix = tfidf.fit_transform(book_df['metadata'])
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

    activities = UserActivity.objects.filter(user_id=user_id, activity_type__in=['view', 'bookmark'])
    activity_weights = {'view': 1, 'bookmark': 5}
    weighted_books = [
        (activity.book.id, activity_weights.get(activity.activity_type, 1))
        for activity in activities
    ]
    logger.debug(f"Weighted books: {weighted_books}")

    recommendations = {}
    id_to_sentiment = book_df.set_index('id')['sentiment'].to_dict()
    user_avg_sentiment = book_df[book_df['id'].isin([book[0] for book in weighted_books])]['sentiment'].mean()

    for book_id, weight in weighted_books:
        idx = book_df[book_df['id'] == book_id].index
        if idx.empty:
            continue
        idx = idx[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_books = [book_df.iloc[i[0]]['id'] for i in sim_scores[1:6]]
        sim_books_filtered = [
            book for book in sim_books
            if abs(id_to_sentiment.get(book, 0) - user_avg_sentiment) < 0.8
        ]
        for book in sim_books_filtered:
            recommendations[book] = recommendations.get(book, 0) + weight

    logger.debug(f"Recommendations: {recommendations}")
    top_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:10]
    return [book[0] for book in top_recommendations]
