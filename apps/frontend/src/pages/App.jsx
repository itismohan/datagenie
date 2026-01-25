
import React, { useEffect, useState } from "react";

export default function App() {
  const [assets, setAssets] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/assets")
      .then(r => r.json())
      .then(setAssets);
  }, []);

  return (
    <div>
      <h1>DataGinie Catalog</h1>
      <ul>
        {assets.map(a => (
          <li key={a.id}>{a.name} ({a.type})</li>
        ))}
      </ul>
    </div>
  );
}
