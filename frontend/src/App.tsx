import React, { useState } from "react";
import MapComponent from "./components/basic_map";
import SpendingReport from "./components/SpendingReport";
import sampleData from "./components/sample_spending_respone.json";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState<'map' | 'spending'>('map');

  return (
    <div className="App">
      <nav style={{ padding: '20px', borderBottom: '1px solid #ddd' }}>
        <button 
          onClick={() => setActiveTab('map')}
          style={{ 
            marginRight: '10px', 
            padding: '10px 20px',
            backgroundColor: activeTab === 'map' ? '#007bff' : '#f8f9fa',
            color: activeTab === 'map' ? 'white' : 'black',
            border: '1px solid #ddd',
            borderRadius: '4px'
          }}
        >
          Map View
        </button>
        <button 
          onClick={() => setActiveTab('spending')}
          style={{ 
            padding: '10px 20px',
            backgroundColor: activeTab === 'spending' ? '#007bff' : '#f8f9fa',
            color: activeTab === 'spending' ? 'white' : 'black',
            border: '1px solid #ddd',
            borderRadius: '4px'
          }}
        >
          Spending Report
        </button>
      </nav>

      {activeTab === 'map' && (
        <div>
          <h1>Map</h1>
          <MapComponent />
        </div>
      )}

      {activeTab === 'spending' && (
        <SpendingReport data={sampleData} />
      )}
    </div>
  );
}

export default App;
