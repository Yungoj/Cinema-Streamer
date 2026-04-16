let tg = null;
let userId = null;
let allMovies = [];
let bgInterval = null;
let currentBgIndex = 0;

try {
    tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
    userId = tg.initDataUnsafe?.user?.id;
} catch(e) {}

document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
});

async function loadMovies() {
    const loading = document.getElementById('loading');
    const grid = document.getElementById('movies-grid');
    const empty = document.getElementById('empty-state');

    try {
        const res = await fetch('/api/movies');
        const movies = await res.json();
        allMovies = movies;
        loading.style.display = 'none';

        populateGenres(movies);
        renderMovies(movies);
        startBackgroundSlideshow(movies);
    } catch(e) {
        loading.textContent = 'Failed to load movies';
    }
}

function populateGenres(movies) {
    const select = document.getElementById('genre-select');
    const genres = [...new Set(movies.map(m => m.genre).filter(Boolean))];
    genres.sort();
    select.innerHTML = '<option value="">All Genres</option>';
    genres.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g;
        opt.textContent = g;
        select.appendChild(opt);
    });
}

function renderMovies(movies) {
    const grid = document.getElementById('movies-grid');
    const empty = document.getElementById('empty-state');

    if (movies.length === 0) {
        grid.innerHTML = '';
        empty.style.display = 'block';
        return;
    }
    empty.style.display = 'none';

    grid.innerHTML = movies.map(m => `
        <div class="movie-card" onclick="openMovie(${m.id})" data-poster="${m.poster_url || ''}">
            <img src="${m.poster_url || '/static/placeholder.svg'}" alt="${m.title}" loading="lazy" onerror="this.src='/static/placeholder.svg'">
            <span class="card-type-badge">${m.content_type === 'series' ? 'Series' : 'Movie'}</span>
            <span class="card-id-badge">#${m.id}</span>
            <div class="card-overlay">
                <div class="card-title">${m.title}</div>
                <div class="card-genre">${m.genre || ''}</div>
            </div>
        </div>
    `).join('');
}

function startBackgroundSlideshow(movies) {
    if (bgInterval) clearInterval(bgInterval);
    const posters = movies.map(m => m.poster_url).filter(Boolean);
    if (posters.length === 0) return;

    const bg = document.getElementById('bg-slideshow');

    function setBg() {
        bg.style.backgroundImage = `url(${posters[currentBgIndex]})`;
        currentBgIndex = (currentBgIndex + 1) % posters.length;
    }

    setBg();
    bgInterval = setInterval(setBg, 6000);
}

function changeBgTo(posterUrl) {
    if (!posterUrl) return;
    const bg = document.getElementById('bg-slideshow');
    bg.style.opacity = '0.25';
    bg.style.backgroundImage = `url(${posterUrl})`;
}

document.getElementById('search-input').addEventListener('input', filterMovies);
document.getElementById('genre-select').addEventListener('change', filterMovies);

function filterMovies() {
    const search = document.getElementById('search-input').value.toLowerCase();
    const genre = document.getElementById('genre-select').value;

    let filtered = allMovies;
    if (search) {
        filtered = filtered.filter(m => m.title.toLowerCase().includes(search));
    }
    if (genre) {
        filtered = filtered.filter(m => m.genre === genre);
    }
    renderMovies(filtered);
}

async function openMovie(movieId) {
    const modal = document.getElementById('movie-modal');
    const body = document.getElementById('modal-body');
    body.innerHTML = '<div class="loading">Loading...</div>';
    modal.style.display = 'flex';

    try {
        const res = await fetch(`/api/movies/${movieId}`);
        const movie = await res.json();

        changeBgTo(movie.poster_url);

        let html = '';

        if (movie.poster_url) {
            html += `<img class="modal-poster" src="${movie.poster_url}" alt="${movie.title}" onerror="this.style.display='none'">`;
        }

        html += `<div class="modal-info">`;
        html += `<div class="modal-title">${movie.title}</div>`;
        html += `<div class="modal-genre">${movie.genre || 'N/A'} &bull; ${movie.content_type === 'series' ? 'Series' : 'Movie'}</div>`;
        html += `<div class="modal-id">ID: #${movie.id}</div>`;

        if (movie.description) {
            html += `<div class="modal-description">${movie.description}</div>`;
        }

        if (movie.trailer_url) {
            const embedUrl = getYoutubeEmbed(movie.trailer_url);
            if (embedUrl) {
                html += `<div class="section-title">Trailer</div>`;
                html += `<div class="trailer-container"><iframe src="${embedUrl}" allowfullscreen></iframe></div>`;
            }
        }

        if (movie.content_type === 'movie' && movie.files) {
            const parts = {};
            const regular = [];

            movie.files.forEach(f => {
                if (f.part_number) {
                    if (!parts[f.part_number]) parts[f.part_number] = [];
                    parts[f.part_number].push(f);
                } else {
                    regular.push(f);
                }
            });

            if (regular.length > 0) {
                html += `<div class="section-title">Download</div>`;
                regular.forEach(f => {
                    const qualityLabel = f.quality && f.quality !== 'default' ? f.quality : '';
                    html += `<button class="download-btn" onclick="downloadFile('${f.file_id}', this)">
                        <span class="btn-label">Download${qualityLabel ? '' : ' Movie'}</span>
                        ${qualityLabel ? `<span class="btn-quality">${qualityLabel}</span>` : ''}
                    </button>`;
                });
            }

            const partNums = Object.keys(parts).sort((a, b) => a - b);
            if (partNums.length > 0) {
                partNums.forEach(pn => {
                    html += `<div class="section-title">Part ${pn}</div>`;
                    parts[pn].forEach(f => {
                        const qualityLabel = f.quality && f.quality !== 'default' ? f.quality : '';
                        html += `<button class="download-btn" onclick="downloadFile('${f.file_id}', this)">
                            <span class="btn-label">Download Part ${pn}</span>
                            ${qualityLabel ? `<span class="btn-quality">${qualityLabel}</span>` : ''}
                        </button>`;
                    });
                });
            }
        }

        if (movie.content_type === 'series' && movie.seasons) {
            html += `<div class="section-title">Seasons</div>`;
            html += `<div class="season-tabs">`;
            movie.seasons.forEach((s, i) => {
                html += `<button class="season-tab ${i === 0 ? 'active' : ''}" onclick="switchSeason(this, ${s.id})">Season ${s.season_number}</button>`;
            });
            html += `</div>`;

            movie.seasons.forEach((s, i) => {
                html += `<div class="episode-list season-episodes" id="season-${s.id}" style="${i > 0 ? 'display:none' : ''}">`;
                if (s.episodes && s.episodes.length > 0) {
                    s.episodes.forEach(ep => {
                        html += `<button class="episode-btn" onclick="downloadFile('${ep.file_id}', this)">
                            <span class="ep-number">E${ep.episode_number}</span>
                            <span class="ep-title">${ep.caption || 'Episode ' + ep.episode_number}</span>
                        </button>`;
                    });
                } else {
                    html += `<div style="padding:16px; color:var(--text-secondary); text-align:center;">No episodes yet</div>`;
                }
                html += `</div>`;
            });
        }

        html += `</div>`;
        body.innerHTML = html;
    } catch(e) {
        body.innerHTML = '<div class="loading">Failed to load movie details</div>';
    }
}

function switchSeason(btn, seasonId) {
    btn.parentElement.querySelectorAll('.season-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.season-episodes').forEach(el => el.style.display = 'none');
    document.getElementById('season-' + seasonId).style.display = 'block';
}

function closeModal() {
    document.getElementById('movie-modal').style.display = 'none';
    const bg = document.getElementById('bg-slideshow');
    bg.style.opacity = '0.15';
}

document.getElementById('movie-modal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});

async function downloadFile(movieId, btn) {
    if (!userId) {
        showToast('Please open this app from Telegram');
        return;
    }

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-label">Sending to chat...</span>';

    try {
        const res = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_id: userId, 
                movie_id: movieId  // Now sending movie_id instead of file_id
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast('File sent to your Telegram chat!');
            btn.innerHTML = '<span class="btn-label">Sent!</span>';
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 2000);
        } else {
            showToast('Failed: ' + (data.error || 'Unknown error'));
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch(e) {
        showToast('Network error. Try again.');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

document.getElementById('request-btn').addEventListener('click', async () => {
    const input = document.getElementById('request-input');
    const text = input.value.trim();
    if (!text) return;

    const status = document.getElementById('request-status');
    try {
        const res = await fetch('/api/requests', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId || 0,
                username: tg?.initDataUnsafe?.user?.username || 'anonymous',
                request_text: text
            })
        });
        const data = await res.json();
        if (data.success) {
            status.textContent = 'Request submitted successfully!';
            input.value = '';
        } else {
            status.textContent = 'Failed to submit request.';
        }
    } catch(e) {
        status.textContent = 'Network error. Try again.';
    }
    setTimeout(() => status.textContent = '', 3000);
});

function getYoutubeEmbed(url) {
    if (!url) return null;
    let videoId = null;
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/
    ];
    for (const p of patterns) {
        const match = url.match(p);
        if (match) { videoId = match[1]; break; }
    }
    return videoId ? `https://www.youtube.com/embed/${videoId}` : null;
}

function showToast(message) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

loadMovies();
