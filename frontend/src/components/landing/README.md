# Landing Pages

This directory contains 10 unique landing page designs that rotate randomly for unauthenticated users.

## Structure

- `LandingPageWrapper.tsx` - Wrapper component that randomly selects and displays one of 10 landing pages
- `LandingPage1.tsx` through `LandingPage10.tsx` - Individual landing page components
- `TeachrLogo.tsx` - Text-based Teachr logo component
- `landing.scss` - Shared styles for landing pages

## Design Styles

1. **LandingPage1**: Neo-Brutalism - Matches existing system design (bold borders, cream background)
2. **LandingPage2**: Minimalist - Clean, lots of white space, simple typography
3. **LandingPage3**: Gradient Modern - Vibrant gradients, smooth animations
4. **LandingPage4**: Glassmorphism - Frosted glass effects, blur backgrounds
5. **LandingPage5**: Dark Mode Elegant - Dark theme with neon accents
6. **LandingPage6**: Card-Based Layout - Feature cards, grid system
7. **LandingPage7**: Split-Screen - Image/content split, modern layout
8. **LandingPage8**: Animated Hero - Subtle animations, engaging visuals
9. **LandingPage9**: Magazine Style - Editorial layout, bold typography
10. **LandingPage10**: Interactive Showcase - Hover effects, interactive elements

## Random Selection

- Uses `sessionStorage` to persist the selected landing page for the user's session
- Each user sees one random landing page when they first visit
- The same page is shown throughout their session

## Screenshot

All landing pages use a placeholder screenshot at:
- Path: `/landing-screenshots/home-screen-placeholder.png`
- Location: `frontend/public/landing-screenshots/`

**To replace the placeholder:**
1. Add your screenshot as `home-screen-placeholder.png` in `frontend/public/landing-screenshots/`
2. The image will automatically be used by all landing pages

## Features Highlighted

All landing pages highlight these features (in non-technical language):
- Personalized learning that adapts to each student
- AI-powered tutoring with real-time help
- Progress tracking and improvement monitoring
- Interactive math questions
- Practice at your own pace
- Instant feedback on answers
- K-12 grade coverage

## CTA Variations

Each page has a unique call-to-action button text:
1. "Start Learning Free"
2. "Get Started"
3. "Try It Free"
4. "Start Today"
5. "Start Learning"
6. "Start Practicing"
7. "Learn More"
8. "Get Started"
9. "Start Learning"
10. "Start Learning"

All CTAs redirect to `/login` page.

## Responsive Design

All landing pages are fully responsive:
- Mobile-first approach
- Breakpoints at 768px
- Optimized for all screen sizes

## Integration

Landing pages are integrated via `index.tsx`:
- Unauthenticated users visiting `/` see a random landing page
- Authenticated users visiting `/` see the main App
- All existing functionality remains intact

