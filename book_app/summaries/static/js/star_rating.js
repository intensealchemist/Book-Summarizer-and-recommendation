document.addEventListener('DOMContentLoaded', function () {
    const stars = document.querySelectorAll('.star-rating .star');
    const starRatingElement = document.getElementById('star-rating');
    
    if (!starRatingElement) {
        console.error('Error: Element with id "star-rating" not found in the DOM.');
        return;
    }

    const bookId = starRatingElement.dataset.bookId;

    if (!bookId) {
        console.error('Error: "data-book-id" attribute is missing or empty.');
        return;
    }

    stars.forEach((star) => {
        star.addEventListener('click', function () {
            const rating = parseInt(this.dataset.value, 10);
            if (!rating || rating < 1 || rating > 5) {
                console.error('Invalid rating:', rating);
                return;
            }

            console.log(`Submitting rating: ${rating} for book ID: ${bookId}`);
            
            fetch(`/api/rate-book/${bookId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
                body: JSON.stringify({ star_rating: rating }),
            })
            .then((response) => {
                if (!response.ok) {
                    return response.json().then((err) => {
                        throw new Error(err.error || 'Failed to submit rating');
                    });
                }
                return response.json();
            })
            .then((data) => {
                document.getElementById('rating-message').textContent = data.message || 'Rating submitted!';
            })
            .catch((error) => {
                console.error('Error:', error.message);
                document.getElementById('rating-message').textContent = error.message || 'An error occurred.';
            });
        });
    });
});
