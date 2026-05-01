import { useState, useEffect } from 'react';
import './App.css';

function PlayerCard({ player }) {
    return (
        <div className="player-card">
            <div className="player-name">
                {player.name}<span className="tagline">#{player.tagline}</span>
            </div>
            <div className="player-rank">{player.rank}</div>
            <div className="player-stats">
                {player.wins}W · {player.losses}L · {player.winrate}% WR
            </div>
        </div>
    );
}

function App() {
    const [players, setPlayers] = useState([]);
    const [inChampSelect, setInChampSelect] = useState(false);

    useEffect(() => {
        async function checkChampSelect() {
            try {
                const response = await fetch("http://127.0.0.1:8000/champ-select?region=euw");
                const data = await response.json();
                setInChampSelect(data.in_champ_select);
                setPlayers(data.players);
            } catch (err) {
                console.error("Backend not reachable", err);
            }
        }
        
        checkChampSelect();  // run once immediately
        const interval = setInterval(checkChampSelect, 3000);  // then every 3 seconds
        return () => clearInterval(interval);  // cleanup on unmount
    }, []);

    return (
        <div className="cards-container">
            {!inChampSelect && <p>Waiting for champ select...</p>}
            {players.map((p, i) => <PlayerCard key={i} player={p} />)}
        </div>
    );
}

export default App;