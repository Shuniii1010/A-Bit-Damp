# Process

## 1. Creative Starting Point

This project grew out of my everyday experience of Hong Kong’s humid weather.

My initial idea was to draw ink blots at different weather-station locations on a map of Hong Kong. The higher the humidity, the denser and darker the ink blot would become, with a wider spread; at lower humidity levels, the blot would appear lighter and smaller. As humidity changed throughout the day, the ink blots would continuously expand or contract on the map, creating an animation.

## 2. Creating a Visual Concept with image-2

Before writing any code, I used the image-2 model to generate a concept image of my intended result. I provided the model with a relative humidity map of Hong Kong, references for the ink-blot style, and references for the ink-wash color palette to clarify my requirements.

The generated concept image helped me establish the project’s visual direction and made the subsequent coding process more efficient.

## 3. Using Codex to Understand the Assignment Requirements

I asked Codex to read the course’s Assignment 2 document and summarize its requirements in Chinese.

I referred to the `tidal-streams` example provided by the instructor. This example led me to use animated WebP instead of GIF because WebP can reduce the file size while preserving animation and can also be displayed directly in a GitHub README.

## 4. Data Sources and Extraction

I asked Codex to analyze the network requests behind the Hong Kong Observatory’s regional weather webpage and identify the JSON data used by the page.

Codex helped me extract and save the raw JSON response for each weather station. These files are stored directly in `data/` exactly as returned by the server, and the plotting code does not modify them. This allows the work to be regenerated from a fixed dataset in the repository without being affected by later forecast updates on the Hong Kong Observatory website.

The dataset contains 28 locations. Of these, 26 contain the complete humidity forecasts required for the project. Tai Mei Tuk and Yuen Long Park had no available humidity values for the target date. I retained the raw JSON files for these two locations but excluded them from the visualization rather than treating the missing values as zero.

## 5. Defining the MVP

Before writing the code, Codex and I defined the following MVP:

1. Read the hourly humidity forecast for the entire day of September 25.
2. Select one time point every two hours, from 00:00 to 22:00, producing 12 frames in total.
3. Use each weather station’s latitude and longitude to place its ink blot in the correct location on the map.
4. Make each ink blot larger and darker as humidity increases.
5. Preserve the same texture for each station across all frames while changing only its size and opacity.
6. Generate one static PNG and one animated WebP.
7. Additionally, generate an interactive Folium web map that supports playback, zooming, and clicking.
8. Use Hong Kong time, UTC+8, consistently throughout the project.

We also discussed whether Pygame and Folium would conflict with each other. In the end, we adopted a combined approach: Pygame and Pillow generate the irregular ink blots and render the static and animated frames, while Folium handles the interactive map, geographic positioning, zooming, pop-ups, and timeline. Both outputs use the same dataset and the same rules for converting humidity values into ink-blot styles.

## 6. Geographic Coordinates and Map Positioning

I was concerned that the weather stations’ coordinates might not align accurately with their positions on a map image, so I asked Codex to analyze the positioning methods used by the Hong Kong Observatory and online mapping platforms.

The final code uses the Web Mercator projection to convert each station’s latitude and longitude into map pixel coordinates. The basemap uses Esri’s Light Gray Canvas map tiles. The downloaded tiles are stitched together and stored in `data/`, so the map does not need to be downloaded again each time the PNG and WebP files are generated.

The Folium web map uses the stations’ latitude and longitude directly, ensuring that the ink blots remain in the correct geographic locations when the user zooms or pans the map.

## 7. Implementing the Ink-Blot Effect

Initially, I planned to complete the MVP using ordinary circles and then gradually replace them with ink blots. Codex suggested that, instead of relying only on `pygame.draw.circle()`, I could create an ink-like effect by layering multiple irregular shapes.

It is crucial to fix the random seed. If the ink dots are randomly generated for each frame, the animation will keep flickering, and the audience will not be able to determine whether the change comes from humidity or random texture. Now, the same ink pattern is used in all frames, with only the size and concentration changing.

## 8. What I kept

I retained most of the code written by Codex, including the conversion from humidity to ink dots and the website interaction. After we discussed the details in detail, the Astra model was basically able to meet my requirements in one go.

## 9. What I reject

The initial output file named by Codex were `humidity.png` and `humidity.webp`. I changed to `plot.png` and `plot.webp` according to the template.

In the original code of Codex, the `humidity_to_style(humidity)`program in `humidity.py`
converts humidity into: `diameter`, `opacity`, and `blur`. 

The original conversion was based on a continuous range of 50% to 100%:
 `t = max(0.0, min(1.0, (humidity - 50) / 50))`. 
 
 Although this would make the visual differences between different ink dots larger, overall, the high humidity weather in Hong Kong cannot be reflected.

Therefore, I want to change the continuous change to ten fixed styles:

`0～10%`
`10～20%`
`20～30%`
`30～40%`
`40～50%`

`50～60%`
`60～70%`
`70～80%`
`80～90%`
`90～100%`

I only changed the calculation method of `t` to: `t = max(0.0, min(1.0, (math.ceil(humidity / 10) - 1) / 9))`.


Subsequently, I also updated the `frame()` function in the final image/webpage generation code. 

I changed `for n, value in enumerate((60,80,95)):` to `for n, value in enumerate((10, 50, 100)):`.

As a result, in the left image, the effects of 10%, 50%, and 100% humidity will be displayed.

## 10. The final version

After completing the work, I asked Codex to review our previous conversation and summarise everything it had helped me with. I then used that summary to create the first draft of this `PROCESS.md` file and added more explanation .