document.addEventListener("DOMContentLoaded", () => {
    fetchCategories();
    fetchBooks();
});

function fetchCategories() {
    fetch('/api/categories/')  // Adjust this URL to your actual categories endpoint
        .then(response => response.json())
        .then(categories => {
            const categoryList = document.getElementById('category-list');
            categories.forEach(category => {
                const li = document.createElement('li');
                li.textContent = category.name;
                categoryList.appendChild(li);
            });
        })
        .catch(error => console.error("Error fetching categories:", error));
}

function fetchBooks() {
    fetch('/api/books/')  // Adjust this URL to your actual books endpoint
        .then(response => response.json())
        .then(books => {
            const bookList = document.getElementById('book-list');
            books.forEach(book => {
                const li = document.createElement('li');
                li.textContent = `${book.title} by ${book.author}`;
                bookList.appendChild(li);
            });
        })
        .catch(error => console.error("Error fetching books:", error));
}
