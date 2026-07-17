package demo.checkout

class CheckoutGate {
    fun canCheckout(enabled: Boolean, loggedIn: Boolean): Boolean {
        return enabled && loggedIn
    }
}
