const testPlayers = [
    { name: "mouftz", tagline: "real" },
    { name: "mouftz", tagline: "real" },
    { name: "mouftz", tagline: "real" },
    { name: "mouftz", tagline: "real" },
    { name: "mouftz", tagline: "real" }
];

async function loadPlayers() {
    const response = await fetch("http://127.0.0.1:8000/players?region=na", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(testPlayers)
    });
    
    const players = await response.json();
    renderPlayers(players);
}

function renderPlayers(players) {
    const container = document.getElementById("cards-container");
    container.innerHTML = "";  // clear any existing cards
    
    for (const p of players) {
        const card = document.createElement("div");
        card.className = "player-card";
        card.innerHTML = `
            <div class="player-name">${p.name}<span class="tagline">#${p.tagline}</span></div>
            <div class="player-rank">${p.rank}</div>
            <div class="player-stats">
                <span>${p.wins}W</span> · <span>${p.losses}L</span> · <span>${p.winrate}% WR</span>
            </div>
        `;
        container.appendChild(card);
    }
}

loadPlayers();