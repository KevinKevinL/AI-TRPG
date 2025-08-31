// pages/api/map_state/[map_id].js
export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  const { map_id } = req.query;

  if (!map_id) {
    return res.status(400).json({ message: 'Map ID is required' });
  }

  try {
    // 转发请求到后端
    const response = await fetch(`http://localhost:8000/api/map_state/${map_id}`);
    
    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    console.error('Error fetching map state:', error);
    res.status(500).json({ message: 'Failed to fetch map state', error: error.message });
  }
}
