document.addEventListener('DOMContentLoaded', () => {
    // Basic Table Sorting Logic
    const table = document.querySelector('.product-table');
    if (!table) return;

    const headers = table.querySelectorAll('th');

    headers.forEach((header, index) => {
        // Skip Rank column
        if (index === 0) return;

        header.style.cursor = 'pointer';
        header.title = 'Click to sort';

        // Add sort icon placeholder
        header.innerHTML += ' <i class="fas fa-sort" style="font-size: 0.8em; color: #64748b; margin-left: 5px;"></i>';

        header.addEventListener('click', () => {
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const isAscending = header.classList.contains('sort-asc');

            // Clear all sort classes
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
                const icon = h.querySelector('i.fa-sort, i.fa-sort-up, i.fa-sort-down');
                if (icon) {
                    icon.className = 'fas fa-sort';
                    icon.style.color = '#64748b';
                }
            });

            // Set new sort direction
            header.classList.toggle('sort-asc', !isAscending);
            header.classList.toggle('sort-desc', isAscending);

            const newIcon = header.querySelector('i');
            if (newIcon) {
                newIcon.className = !isAscending ? 'fas fa-sort-up' : 'fas fa-sort-down';
                newIcon.style.color = '#38bdf8';
            }

            rows.sort((a, b) => {
                let cellA = a.querySelectorAll('td')[index].innerText.trim();
                let cellB = b.querySelectorAll('td')[index].innerText.trim();

                // Handle numbers and currency
                if (cellA.includes('₹')) {
                    cellA = parseFloat(cellA.replace(/[^0-9.-]+/g, ""));
                    cellB = parseFloat(cellB.replace(/[^0-9.-]+/g, ""));
                } else if (!isNaN(parseFloat(cellA)) && isFinite(cellA)) {
                    cellA = parseFloat(cellA);
                    cellB = parseFloat(cellB);
                }

                if (cellA < cellB) return isAscending ? 1 : -1;
                if (cellA > cellB) return isAscending ? -1 : 1;
                return 0;
            });

            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));

            // Update rank pills to maintain visual order 1,2,3...
            const updatedRows = tbody.querySelectorAll('tr');
            updatedRows.forEach((row, i) => {
                const rankPill = row.querySelector('.rank-pill');
                if (rankPill) rankPill.innerText = i + 1;

                // Keep top-row styling on the actual top row
                if (i === 0) row.classList.add('top-row');
                else row.classList.remove('top-row');
            });
        });
    });

    // Dynamic AI Weighting Logic
    const priceRange = document.getElementById('priceWeight');
    const ratingRange = document.getElementById('ratingWeight');
    const sentimentRange = document.getElementById('sentimentWeight');
    const resetBtn = document.getElementById('resetWeights');

    if (priceRange && ratingRange && sentimentRange) {
        const wrapper = document.getElementById('resultsWrapper');
        
        const updateScores = () => {
            if (!wrapper) return;
            const minPrice = parseFloat(wrapper.dataset.minPrice);
            const maxPrice = parseFloat(wrapper.dataset.maxPrice);
            const wPrice = parseInt(priceRange.value);
            const wRating = parseInt(ratingRange.value);
            const wSentiment = parseInt(sentimentRange.value);
            const total = wPrice + wRating + wSentiment || 1;

            // Update UI labels
            document.getElementById('priceWeightVal').innerText = Math.round(wPrice / total * 100) + '%';
            document.getElementById('ratingWeightVal').innerText = Math.round(wRating / total * 100) + '%';
            document.getElementById('sentimentWeightVal').innerText = Math.round(wSentiment / total * 100) + '%';

            const rows = Array.from(document.querySelectorAll('.product-row'));
            rows.forEach(row => {
                const price = parseFloat(row.dataset.price);
                const rating = parseFloat(row.dataset.rating);
                const sentiment = parseFloat(row.dataset.sentiment);
                const discount = parseFloat(row.dataset.discount) || 0;

                // Price Score
                let pScore = 0;
                if (maxPrice > minPrice) {
                    pScore = (1 - (price - minPrice) / (maxPrice - minPrice)) * (wPrice / total * 100);
                } else {
                    pScore = (wPrice / total * 100);
                }

                // Rating Score
                const rScore = (rating / 5.0) * (wRating / total * 100);

                // Sentiment Score
                const sScore = ((sentiment + 1) / 2) * (wSentiment / total * 100);

                // Discount Bonus
                const dScore = Math.min(discount / 20, 5);

                const finalScore = (pScore + rScore + sScore + dScore).toFixed(2);
                row.dataset.score = finalScore;
                
                // AI Score is usually the 2nd to last column
                const cells = row.querySelectorAll('td');
                const scoreCell = cells[cells.length - 2];
                if (scoreCell) scoreCell.innerHTML = `<strong>${finalScore}</strong>`;
            });

            // Re-sort table
            const tbody = document.getElementById('tableBody');
            rows.sort((a, b) => parseFloat(b.dataset.score) - parseFloat(a.dataset.score));
            rows.forEach((row, i) => {
                tbody.appendChild(row);
                const rankPill = row.querySelector('.rank-pill');
                if (rankPill) {
                    if (i === 0) rankPill.innerHTML = '<i class="fas fa-crown"></i>';
                    else rankPill.innerText = i + 1;
                }
                if (i === 0) row.classList.add('top-row');
                else row.classList.remove('top-row');
            });
        };

        [priceRange, ratingRange, sentimentRange].forEach(el => {
            el.addEventListener('input', updateScores);
        });

        resetBtn.addEventListener('click', () => {
            priceRange.value = 40;
            ratingRange.value = 35;
            sentimentRange.value = 25;
            updateScores();
        });
    }
});
