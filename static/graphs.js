srcdata = [
    { "name": "Trent", "value": 5 },
    { "name": "smurf", "value": 9 },
    { "name": "Longername", "value": 3 },
    { "name": "Another", "value": 2 },
    { "name": "more", "value": 1 },
    { "name": "Stuff", "value": 2 },
];





function donughtchart(data, title) {
    const width = 500;
    const height = Math.min(width, 500);
    const pie = d3.pie()
        .padAngle(0.005)
        .sort(null)
        .value(d => d.value);

    const radius = Math.min(width, height) / 2;
    const arc = d3.arc().innerRadius(radius * 0.50).outerRadius(radius - 1);

    const arcs = pie(data);
    const color = d3.scaleOrdinal()
        .domain(data.map(d => d.name))
        .range(d3.quantize(t => { t = t || 0; return d3.interpolateSpectral(t * 0.8 + 0.1); }, data.length).reverse());

    const svg = d3.create("svg")
        .attr("viewBox", [-width / 2, -height / 2, width, height]);

    svg.selectAll("path")
        .data(arcs)
        .join("path")
        .attr("fill", d => color(d.data.name))
        .attr("d", arc)
        .append("title")
        .text(d => `${d.data.name}: ${d.data.value.toLocaleString()}`);

    svg.append("g")
        .attr("font-family", "sans-serif")
        .attr("font-size", 32)
        .attr("text-anchor", "middle")
        .selectAll("text")
        .data(arcs)
        .join("text")
        .attr("transform", d => `translate(${arc.centroid(d)})`)
        .call(text => text.append("tspan")
            .attr("y", "-0.4em")
            .attr("font-weight", "bold")
            .text(d => d.data.name))
        .call(text => text.filter(d => (d.endAngle - d.startAngle) > 0.25).append("tspan")
            .attr("x", 0)
            .attr("y", "0.7em")
            .attr("fill-opacity", 0.7)
            .text(d => d.data.value.toLocaleString()));

    svg.append("text")
        .attr("dominant-baseline", "middle")
        .attr("text-anchor", "middle")
        .attr("font-family", "sans-serif")
        .attr("font-weight", "bold")
        .attr("font-size", 48)
        .text(title);

    return svg.node();
}