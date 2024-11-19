// Import all dependencies, mostly using destructuring for better view.
import { messagingApi, middleware, HTTPFetchError, } from '@line/bot-sdk';
import express from 'express';
// Setup all LINE client and Express configurations.
const clientConfig = {
    channelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN || '',
};
const middlewareConfig = {
    channelSecret: process.env.LINE_CHANNEL_SECRET || '',
};
const PORT = process.env.PORT || 3000;
// Create a new LINE SDK client.
const client = new messagingApi.MessagingApiClient(clientConfig);
// Create a new Express application.
const app = express();
// Function handler to receive the text.
const textEventHandler = async (event) => {
    // Process all variables here.
    // Check if for a text message
    if (event.type !== 'message' || event.message.type !== 'text') {
        return;
    }
    // Process all message related variables here.
    // Check if message is repliable
    if (!event.replyToken)
        return;
    // Create a new message.
    // Reply to the user.
    await client.replyMessage({
        replyToken: event.replyToken,
        messages: [{
                type: 'text',
                text: event.message.text,
            }],
    });
};
// Register the LINE middleware.
// As an alternative, you could also pass the middleware in the route handler, which is what is used here.
// app.use(middleware(middlewareConfig));
// Route handler to receive webhook events.
// This route is used to receive connection tests.
app.get('/', async (_, res) => {
    return res.status(200).json({
        status: 'success',
        message: 'Connected successfully!',
    });
});
// This route is used for the Webhook.
app.post('/callback', middleware(middlewareConfig), async (req, res) => {
    const callbackRequest = req.body;
    const events = callbackRequest.events;
    // Process all the received events asynchronously.
    const results = await Promise.all(events.map(async (event) => {
        try {
            await textEventHandler(event);
        }
        catch (err) {
            if (err instanceof HTTPFetchError) {
                console.error(err.status);
                console.error(err.headers.get('x-line-request-id'));
                console.error(err.body);
            }
            else if (err instanceof Error) {
                console.error(err);
            }
            // Return an error message.
            return res.status(500).json({
                status: 'error',
            });
        }
    }));
    // Return a successful message.
    return res.status(200).json({
        status: 'success',
        results,
    });
});
// Create a server and listen to it.
app.listen(PORT, () => {
    console.log(`Application is live and listening on port ${PORT}`);
});
