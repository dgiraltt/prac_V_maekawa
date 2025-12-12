from maekawaMutex import MaekawaMutex
from threading import Thread


def run_algorithm():
    """Creates the distributed system as a MaekawaMutex object and starts it."""
    maekawa_mutex = MaekawaMutex()
    maekawa_mutex.run()


if __name__ == "__main__":
    mutex_thread = Thread(target=run_algorithm)
    mutex_thread.start()

    mutex_thread.join()
    print("Done")

