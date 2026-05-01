# LoL Overlay

A Mac desktop overlay app for League of Legends that auto-detects champion select and displays summoner ranks, winrates, and stats for all players in real time. Inspired by Porofessor and OP.GG Desktop, which don't have native Mac support.

## Tech Stack

- **Backend:** Python, FastAPI, async/await with httpx for parallel Riot API calls
- **Frontend:** React (Vite), polling-based updates
- **Integration:** Local LCU API for champ select detection, Riot API for ranked data

## Architecture

The backend runs locally and exposes endpoints that:
1. Read the League Client lockfile to authenticate with the LCU
2. Detect when champ select starts and extract all visible players
3. Fetch ranked stats for all players in parallel from the Riot API

The React frontend polls the backend every 3 seconds and renders player cards when champ select is active.

## Running locally

Backend:
