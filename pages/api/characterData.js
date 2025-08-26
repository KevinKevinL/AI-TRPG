// pages/api/characterData.js

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Only GET requests are allowed' });
  }

  const { character_id } = req.query;
  if (!character_id) {
    return res.status(400).json({ error: 'character_id is required' });
  }

  try {
    const pythonBackendUrl = `http://localhost:8000/api/character_data?character_id=${encodeURIComponent(character_id)}`;
    const backendResponse = await fetch(pythonBackendUrl);

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Python backend returned an error.');
    }

    const data = await backendResponse.json();
    return res.status(200).json(data);
  } catch (err) {
    console.error('Error in /api/characterData:', err.message);
    return res.status(500).json({ error: 'Failed to fetch character data from backend.' });
  }
}


