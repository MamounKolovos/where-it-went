import React, { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import places from "./mockdata.json";

mapboxgl.accessToken = "pk.eyJ1IjoicmFoaW1hYXRoYXI1IiwiYSI6ImNtZWU4cjZnNTBqM3IyanBsZHF5NnR6MHUifQ.P0xqeJo71exDfW0vEaq1LQ";

function MapComponent() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [showPrompt, setShowPrompt] = useState(true);

  const lat = 38.83125;  
  const lng = -77.3143;

  useEffect(() => {
    if (map.current || showPrompt) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current!,
      style: "mapbox://styles/mapbox/streets-v11",
      center: [lng, lat],
      zoom: 14,
    });

    map.current.on("load", function () {
     
      let myDiv = document.createElement("div");
      myDiv.style.width = "20px";
      myDiv.style.height = "20px";
      myDiv.style.background = "blue";
      myDiv.style.borderRadius = "50%";

      let myMarker = new mapboxgl.Marker(myDiv)
        .setLngLat([lng, lat])
        .setPopup(new mapboxgl.Popup().setHTML("<div>User Location</div>"))
        .addTo(map.current!);

      myMarker.togglePopup();

      let bounds = new mapboxgl.LngLatBounds();
      bounds.extend([lng, lat]);

   
      for (let i = 0; i < places.places.length; i++) {
        let place = places.places[i];

        let div = document.createElement("div");
        div.style.width = "20px";
        div.style.height = "20px";
        div.style.background = "red";
        div.style.borderRadius = "50%";

        let text = "<div><strong>" + place.text + "</strong><br>";
        for (let j = 0; j < place.types.length; j++) {
          text = text + place.types[j].replace(/_/g, " ") + "<br>";
        }
        text = text + "</div>";

        new mapboxgl.Marker(div).setLngLat([place.longitude, place.latitude]).setPopup(new mapboxgl.Popup().setHTML(text)).addTo(map.current!);

        bounds.extend([place.longitude, place.latitude]);
      }

      map.current!.fitBounds(bounds, { padding: 50 });
    });
  }, [showPrompt]);

  return (
    <div>
      {showPrompt && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "white" }}>
          <div>
            <p>Share your location to see nearby places</p>
            <button onClick={() => setShowPrompt(false)}>Allow Access</button>
            <p>Default: George Mason University</p>
          </div>
        </div>
      )}
      <div ref={mapContainer} style={{ width: "100%", height: "500px" }}></div>
    </div>
  );
}

export default MapComponent;
