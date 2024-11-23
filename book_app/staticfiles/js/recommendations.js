    document.addEventListener("DOMContentLoaded", async () => {
        const recommendationsContainer = document.querySelector(".recommendations-section");
        recommendationsContainer.innerHTML = "<p>Loading recommendations...</p>";
        
        try {
            const response = await fetch("{% url 'recommendations' %}");
            const data = await response.json();
            recommendationsContainer.innerHTML = "";

            if (data.length > 0) {
                const list = document.createElement("ul");
                data.forEach(book => {
                    const listItem = document.createElement("li");
                    listItem.innerHTML = `<h3>${book.title}</h3><p>${book.author}</p><p>${book.summary}</p>`;
                    list.appendChild(listItem);
                });
                recommendationsContainer.appendChild(list);
            } else {
                recommendationsContainer.innerHTML = "<p>No recommendations available.</p>";
            }
        } catch (error) {
            recommendationsContainer.innerHTML = "<p style='color: red;'>Failed to load recommendations.</p>";
        }
    });

