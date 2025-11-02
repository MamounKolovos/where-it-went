import React, { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import places from "./mockdata.json";
import SpendingReport from "./SpendingReport";
import spendingData from "./sample_spending_respone.json";

mapboxgl.accessToken = "pk.eyJ1IjoicmFoaW1hYXRoYXI1IiwiYSI6ImNtZWU4cjZnNTBqM3IyanBsZHF5NnR6MHUifQ.P0xqeJo71exDfW0vEaq1LQ";

function MapComponent() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [showPrompt, setShowPrompt] = useState(true);
  const [isReportVisible, setIsReportVisible] = useState(false);

  const lat = 38.83125;
  const lng = -77.3143;

  const handleCloseReport = () => {
    setIsReportVisible(false);
  };

  const handleShowReport = () => {
    setIsReportVisible(true);
  };

  useEffect(() => {
    if (map.current || showPrompt) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current!,
      style: "mapbox://styles/mapbox/streets-v11",
      center: [lng, lat],
      zoom: 14,
    });

    map.current.on("load", function () {
      let bounds = new mapboxgl.LngLatBounds();
      bounds.extend([lng, lat]);

      places.places.forEach((place) => {
        if (place.text === "George Mason University") {
          let div = document.createElement("div");
          div.style.width = "20px";
          div.style.height = "20px";
          div.style.background = "red";
          div.style.borderRadius = "50%";

          const marker = new mapboxgl.Marker(div)
            .setLngLat([place.longitude, place.latitude])
            .addTo(map.current!);

          div.addEventListener("click", handleShowReport);
        } else {
          let div = document.createElement("div");
          div.style.width = "20px";
          div.style.height = "20px";
          div.style.background = "blue";
          div.style.borderRadius = "50%";

          new mapboxgl.Marker(div)
            .setLngLat([place.longitude, place.latitude])
            .setPopup(new mapboxgl.Popup().setHTML(place.text))
            .addTo(map.current!);
        }

        bounds.extend([place.longitude, place.latitude]);
      });

      map.current!.fitBounds(bounds, { padding: 50 });
    });
  }, [showPrompt]);

  return (
    <div>
      {showPrompt && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "white",
          }}
        >
          <div>
            <p>Share your location to see nearby places</p>
            <button onClick={() => setShowPrompt(false)}>Allow Access</button>
            <p>Default: George Mason University</p>
          </div>
        </div>
      )}
      <div
        ref={mapContainer}
        style={{ width: "100%", height: "500px" }}
      ></div>
      {isReportVisible && (
        <SpendingReport data={spendingData} onClose={handleCloseReport} />
      )}
    </div>
  );
}

export default MapComponent;
