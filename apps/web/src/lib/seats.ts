/** Tunisian governorate seats (name, latitude, longitude): plain data, usable on the server and in the browser. */

export const SEATS: [string, number, number][] = [
  ["Tunis", 36.81, 10.18], ["Ariana", 36.86, 10.19], ["Ben Arous", 36.75, 10.22], ["Manouba", 36.81, 10.1],
  ["Nabeul", 36.45, 10.73], ["Zaghouan", 36.4, 10.14], ["Bizerte", 37.27, 9.87], ["Béja", 36.73, 9.18],
  ["Jendouba", 36.5, 8.78], ["Le Kef", 36.17, 8.71], ["Siliana", 36.08, 9.37], ["Sousse", 35.83, 10.64],
  ["Monastir", 35.78, 10.83], ["Mahdia", 35.5, 11.06], ["Sfax", 34.74, 10.76], ["Kairouan", 35.68, 10.1],
  ["Kasserine", 35.17, 8.83], ["Sidi Bouzid", 35.04, 9.48], ["Gabès", 33.88, 10.1], ["Médenine", 33.35, 10.5],
  ["Tataouine", 32.93, 10.45], ["Gafsa", 34.43, 8.78], ["Tozeur", 33.92, 8.13], ["Kébili", 33.7, 8.97],
];

/** Nearest governorate seat, or null when the point is outside Tunisia (more than ~60 km from any seat). */
export function nearestSeat(lat: number, lon: number): string | null {
  let best = SEATS[0];
  let d = Infinity;
  for (const s of SEATS) {
    const dd = (s[1] - lat) ** 2 + ((s[2] - lon) * Math.cos((lat * Math.PI) / 180)) ** 2;
    if (dd < d) {
      d = dd;
      best = s;
    }
  }
  return Math.sqrt(d) * 111 <= 60 ? best[0] : null;
}

