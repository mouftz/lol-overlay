import { useState, useEffect } from 'react';
import './App.css';

function PlayerCard({ player }) {
    const matches = player.recent_matches;
    
    const rankClasses = ['player-rank'];
    if (player.rank === 'Unranked' || player.rank === 'Unknown') {
        rankClasses.push('unranked');
    }
    
    return (
        <div className="player-card">
            <div className="player-name">
                {player.name}<span className="tagline">#{player.tagline}</span>
            </div>
            <div className={rankClasses.join(' ')}>{player.rank}</div>
            <div className="player-stats">
                {player.wins}W · {player.losses}L · {player.winrate}% WR
            </div>
            {matches.results.length > 0 && (
                <div className="recent-trend">
                    <div className="trend-dots">
                        {matches.results.map((win, i) => (
                            <span key={i} className={`dot ${win ? 'win' : 'loss'}`} />
                        ))}
                    </div>
                    <div className="trend-label">
                        Last {matches.results.length} · {matches.winrate}% WR
                    </div>
                </div>
            )}
        </div>
    );
}

function App() {
    const [state, setState] = useState("idle");
    const [players, setPlayers] = useState([]);

    useEffect(() => {
        async function fetchState() {
            try {
                const response = await fetch("http://127.0.0.1:8000/champ-select");
                const data = await response.json();
                setState(data.state);
                setPlayers(data.players || []);
            } catch (err) {
                console.error("Backend not reachable", err);
            }
        }
        
        fetchState();
        const intervalMs = state === "loading" || state === "champ_select" ? 5000 : 15000;
        const interval = setInterval(fetchState, intervalMs);
        return () => clearInterval(interval);
    }, [state]);

    return (
        <div className="cards-container">
            {state === "in_game" ? null : (
                <>
                    <div className="status-text">
                        {state === "idle" && "Waiting…"}
                        {state === "loading" && "Loading screen"}
                        {state === "champ_select" && "Champ select"}
                    </div>
                    {players.map((p, i) => <PlayerCard key={i} player={p} />)}
                </>
            )}
        </div>
    );
}

export default App;