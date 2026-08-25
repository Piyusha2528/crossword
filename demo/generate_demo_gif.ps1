# Generates a lightweight README preview. Record this scripted sequence for a full video.
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Bitmap]::new(1000, 560)
$g = [System.Drawing.Graphics]::FromImage($img)
$g.Clear([System.Drawing.Color]::FromArgb(15, 23, 42))
$title = [System.Drawing.Font]::new('Consolas', 24, [System.Drawing.FontStyle]::Bold)
$body = [System.Drawing.Font]::new('Consolas', 15)
$green = [System.Drawing.Brushes]::MediumSpringGreen; $white = [System.Drawing.Brushes]::WhiteSmoke; $muted = [System.Drawing.Brushes]::LightSteelBlue
$g.DrawString('Aster & Row Support Agent - demo', $title, $green, 30, 25)
$lines = @(
'You: How long can I return an unused backpack?',
'Agent: 30 calendar days of delivery for an eligible unused item.',
'Sources: 01-returns-policy-current.md - Standard return window',
'',
'You: Where is ORD-1007 and when should it arrive?',
'Agent: Shipped with UPS. Estimated arrival: August 22, 2026.',
'',
'You: Do you ship internationally?  /  What about Canada?',
'Agent: Canada only; 5-9 business days after dispatch.',
'',
'Agent: Breeze cleaning sources conflict - human confirmation recommended.',
'Evaluation: 20/20 deterministic cases passing'
)
$y=82; foreach ($line in $lines) { $brush = if ($line.StartsWith('You:')) {$green} elseif ($line.StartsWith('Sources:') -or $line.StartsWith('Evaluation:')) {$muted} else {$white}; $g.DrawString($line, $body, $brush, 35, $y); $y += 36 }
$img.Save((Join-Path $PSScriptRoot 'demo.gif'), [System.Drawing.Imaging.ImageFormat]::Gif)
$g.Dispose(); $img.Dispose()
