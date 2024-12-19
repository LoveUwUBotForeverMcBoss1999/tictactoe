document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const stats = JSON.parse(decodeURIComponent(urlParams.get('stats')));

    // Update player names and scores
    document.getElementById('final-p1-name').textContent = stats.player1.name;
    document.getElementById('final-p2-name').textContent = stats.player2.name;
    document.getElementById('final-p1-score').textContent = `Wins: ${stats.p1_wins}`;
    document.getElementById('final-p2-score').textContent = `Wins: ${stats.p2_wins}`;

    // Update match statistics
    document.getElementById('total-matches').textContent = `Total Matches: ${stats.total_matches}`;
    document.getElementById('total-draws').textContent = `Total Draws: ${stats.draws}`;

    // Show last winner if available
    if (stats.last_winner) {
        const lastWinnerText = stats.last_winner === 'draw'
            ? 'Last Game: Draw'
            : `Last Winner: ${stats.last_winner}`;
        document.getElementById('last-winner').textContent = lastWinnerText;
    }
});

function downloadFinalStats() {
    const gameId = window.location.pathname.split('/')[2];
    window.open(`/stats/${gameId}`, '_blank');
}

function goHome() {
    window.location.href = '/';
}